import asyncio
import re

from openai import AsyncOpenAI
from starlette.exceptions import HTTPException

from .secret import Secret
from .settings import Settings
from .logger import LOGGER

secret = Secret()
settings = Settings()


def get_llm_prompt(sentences: list[str], bio: str) -> str:
    # TODO: retrieve a name from selected_area['features'][0]['properties']
    prompt_start = 'Here is the description of the user\'s selected area compared to the world for the reference:'
    prompt_end = f'What the user wrote about themselves: "{bio}" '

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


async def get_llm_commentary(prompt: str) -> str:
    client = AsyncOpenAI(api_key=secret.OPENAI_API_KEY, timeout=40.0)
    LOGGER.debug('looking for %s assistant..', settings.OPENAI_ASSISTANT)
    assistant = [i async for i in client.beta.assistants.list() if i.name == settings.OPENAI_ASSISTANT][0]
    LOGGER.debug('chatGPT instructions: %s', settings.OPENAI_INSTRUCTIONS)
    thread = await client.beta.threads.create()
    current_chunk = ''
    for line in prompt.split('\n'):            
        if len(current_chunk) > 20000:                
            message = await client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=current_chunk
            )
            current_chunk = ''
        current_chunk += line + '\n'
    if current_chunk:
        message = await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=current_chunk
        )
    run = await client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions=settings.OPENAI_INSTRUCTIONS,
    )

    while not run.status == "completed":
        await asyncio.sleep(1)
        run = await client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        LOGGER.debug("openAI thread status: %s", run.status)
        if run.status == "failed":
            raise HTTPException(status_code=400, detail='failed to get OpenAI response')
        
    messages = await client.beta.threads.messages.list(
      thread_id=thread.id
    )

    message_text = ""
    for _, message in messages:
        message_text = message[0].content[0].text.value
        break

    return message_text
