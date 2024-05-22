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


def get_properties(geojson: dict) -> str:
    try:
        if geojson.get('type') == 'FeatureCollection':
            s = '(input GeoJSON is FeatureCollection with multiple properties: '
            s += ', '.join(str(x['properties']) for x in geojson['features'] if x['properties']) or 'not available'
            s += ')'
            return s
        return '(input GeoJSON properties: ' + str(geojson['properties']) + ')'
    except KeyError:
        return '(not available)'


def get_llm_prompt(
        sentences: list[str],
        indicator_description: str,
        bio: str,
        lang: str,
        selected_area_geojson: dict,
        reference_area_geojson: dict,
) -> str:
    reference_area_props = get_properties(reference_area_geojson)
    selected_area_props = get_properties(selected_area_geojson)
    LOGGER.debug('reference_area geom is %s', 'not empty' if reference_area_geojson else 'empty')
    LOGGER.debug('selected_area geom is %s', 'not empty' if selected_area_geojson else 'empty')
    prompt_start = f'Selected area properties: {selected_area_props}'
    if reference_area_geojson and reference_area_geojson != selected_area_geojson:
        prompt_start += f'''
            User's reference area properties: {reference_area_props}

            You are given values for three different areas. Selected region  area is the area you are writing the report about. Reference area is the one picked by user, likely the one that is easy for them to understand, likely being their home or primary region of operation. World values are given to put the difference between selected and reference area into perspective, or to serve as reference when no reference area is given. You may be provided with properties of the geographic objects of selected area and reference area. If properties are not available or lack names, call them "Area you selected" and "Your reference area" respectively. Start report with noting which area you will call what, something like: "Comparing your selected area to your reference area New Zhlobin".
        '''
    prompt_start += f'''
        Here is the description of the user\'s selected area compared to '''
    if reference_area_geojson:
        prompt_start += f'user\'s reference area and the world:'
    else:
        prompt_start += 'the world for the reference:'
    prompt_end = indicator_description + f'''
        User wrote in their bio: "{bio}" '''
    if lang:
        prompt_end += f'''
            User have selected a language: {lang}. Answer in that language.
        '''
    analytics_txt = ';\n'.join(sentences)

    return re.sub(r'\s+', ' ', f'{prompt_start} {analytics_txt} {prompt_end}')
