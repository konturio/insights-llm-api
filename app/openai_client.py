import asyncio
import re

from openai import AsyncOpenAI
from starlette.exceptions import HTTPException

from .secret import Secret
from .settings import Settings
from .logger import LOGGER

secret = Secret()
settings = Settings()


class OpenAIClient:

    def __init__(self):
        self.client = AsyncOpenAI(api_key=secret.OPENAI_API_KEY, timeout=40.0)
        self._assistant = None
        self._model = None

    @property
    async def assistant(self):
        if self._assistant:
            return self._assistant

        LOGGER.debug('looking for %s assistant..', settings.OPENAI_ASSISTANT)
        self._assistant = [i async for i in self.client.beta.assistants.list() if i.name == settings.OPENAI_ASSISTANT][0]
        LOGGER.debug('chatGPT model: %s', self._assistant.model)
        return self._assistant

    @property
    async def model(self):
        assistant = await self.assistant
        return assistant.model

    async def get_llm_commentary(self, prompt: str) -> str:
        '''
        returns chatGPT response for provided prompt
        '''
        thread = await self.client.beta.threads.create()
        current_chunk = ''
        for line in prompt.split('\n'):
            if len(current_chunk) > 20000:
                message = await self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=current_chunk
                )
                current_chunk = ''
            current_chunk += line + '\n'
        if current_chunk:
            message = await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=current_chunk
            )

        # assistant has it's own instructions, but we're able to override them per-run
        assistant = await self.assistant
        LOGGER.debug('chatGPT instructions: %s', settings.OPENAI_INSTRUCTIONS)
        run = await self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions=settings.OPENAI_INSTRUCTIONS,
        )

        while not run.status == "completed":
            await asyncio.sleep(1)
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            LOGGER.debug("openAI thread status: %s", run.status)
            if run.status == "failed":
                raise HTTPException(status_code=400, detail='failed to get OpenAI response')

        messages = await self.client.beta.threads.messages.list(
          thread_id=thread.id
        )

        message_text = ""
        for _, message in messages:
            message_text = message[0].content[0].text.value
            break

        return message_text


def get_area_name_or_tags(geojson: dict) -> str:
    try:
        name = geojson['properties']['tags']['name:en']
        return f'({name})'
    except KeyError:
        return '(OSM tags: ' + ', '.join(geojson['properties']['tags'].values()) + ')'
    finally:
        return ''


def get_llm_prompt(sentences: list[str], bio: str, lang: str, selected_area_geojson: dict, reference_area_geojson: dict) -> str:
    reference_area_name = get_area_name_or_tags(reference_area_geojson)
    selected_area_name = get_area_name_or_tags(selected_area_geojson)
    LOGGER.debug('reference_area geom is %s, reference_area name is %s', 'not empty' if reference_area_geojson else 'empty', reference_area_name)
    LOGGER.debug('selected_area geom is %s, selected_area name is %s', 'not empty' if selected_area_geojson else 'empty', selected_area_name)
    prompt_start = f'Here is the description of the user\'s selected area {selected_area_name} compared to '
    if reference_area_geojson:
        prompt_start += f'user\'s reference area {reference_area_name} and the world:'
    else:
        prompt_start += 'the world for the reference:'
    prompt_end = f'User wrote in their bio: "{bio}" '
    if lang:
        prompt_end += f'''
            User have selected a language: {lang}. Answer in that language.
        '''

    # decide how many sentences we can send respecting max context length
    limit = settings.OPENAI_CONTEXT_LENGTH - len(prompt_start) - len(prompt_end)
    num_sentences = 0
    for s in sentences:
        limit -= len(s)
        if limit < 0:
            break
        num_sentences += 1
    LOGGER.debug('num_sentences: %s of %s', num_sentences, len(sentences))
    analytics_txt = ';\n'.join(sentences[:num_sentences])

    return re.sub(r'\s+', ' ', f'{prompt_start} {analytics_txt} {prompt_end}')
