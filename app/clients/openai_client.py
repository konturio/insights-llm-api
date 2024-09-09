import asyncio
import hashlib
import re

import asyncpg
from openai import AsyncOpenAI
from starlette.exceptions import HTTPException

from app.secret import Secret
from app.logger import LOGGER
from app.db import get_db_conn

secret = Secret()


class OpenAIClient:

    def __init__(self, assistant_name, instructions=None, override_instructions=False):
        self.client = AsyncOpenAI(api_key=secret.OPENAI_API_KEY, timeout=40.0)
        self.assistant_name = assistant_name
        self.instructions = instructions
        self.override_instructions = override_instructions
        self._assistant = None
        self._model = None

    @property
    async def assistant(self):
        if self._assistant:
            return self._assistant

        LOGGER.debug('looking for %s assistant..', self.assistant_name)
        self._assistant = [i async for i in self.client.beta.assistants.list() if i.name == self.assistant_name][0]
        LOGGER.debug('chatGPT model: %s', self._assistant.model)
        return self._assistant

    @property
    async def model(self):
        assistant = await self.assistant
        return assistant.model

    async def get_llm_response_from_cache(self, conn, cache_key, llm_model):
        return await conn.fetchval(
            'select response from llm_cache where hash = $1 and model_name = $2 and response is not null',
            cache_key, llm_model)

    async def get_cached_llm_commentary(self, prompt: str) -> str:
        to_cache = f'instructions: {self.instructions}; prompt: {prompt}'
        LOGGER.debug('\n'.join(prompt.split(';')).replace('"', '\\"'))
        cache_key = hashlib.md5(to_cache.encode("utf-8")).hexdigest()
        llm_model = await self.model

        conn = await get_db_conn()
        if result := await self.get_llm_response_from_cache(conn, cache_key, llm_model):
            await conn.close()
            LOGGER.debug('found LLM response for %s model in the cache', llm_model)
            return result

        tr = conn.transaction()
        await tr.start()
        try:
            # two equal queries will block, the second will fail with duplicate key error
            await conn.execute(
                'insert into llm_cache (hash, request, response, model_name) values ($1, $2, $3, $4)',
                cache_key, to_cache, None, llm_model,
            )
        except asyncpg.exceptions.UniqueViolationError:
            # other transaction saved an LLM response first, return it
            await tr.rollback()
            LOGGER.debug('return response committed by other transaction')
            result = await self.get_llm_response_from_cache(conn, cache_key, llm_model)
            await conn.close()
            return result

        LOGGER.debug('asking LLM for commentary..')
        llm_response = await self.get_llm_commentary(prompt)
        await conn.execute(
            'update llm_cache set response = $1 where hash = $2 and model_name = $3',
            llm_response, cache_key, llm_model,
        )
        await tr.commit()
        await conn.close()
        LOGGER.debug('saved LLM response for hash = %s and model_name = %s', cache_key, llm_model)
        return llm_response


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
        LOGGER.debug('chatGPT instructions: %s', self.instructions)
        if self.override_instructions:
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions=self.instructions,
            )
        else:
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
                additional_instructions=self.instructions,
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
    '''parse input geojson for 'properties', deduplicate, concatenate, truncate and return'''
    properties = []

    def extract_properties(gj: dict) -> list:
        '''
        Recursively extracts properties from the GeoJSON object and updates properties var.
        If the object is a FeatureCollection, it iterates over its features
        and extracts properties from each feature.
        '''
        if gj.get('type') == 'FeatureCollection':
            # Iterate through all features in the FeatureCollection
            for feature in gj.get('features') or []:
                # Recursively extract properties from each feature
                extract_properties(feature)
            return
        # The base case: we're at a leaf and extract actual properties
        properties.append(gj.get('properties'))

    # update `properties` with recursive function
    extract_properties(geojson)
    # remove duplicated and empty props
    deduplicated_properties = set(str(prop) for prop in properties if prop)
    props_str = ', '.join(deduplicated_properties) or 'not available'
    max_properties_length = 2000
    if len(props_str) > max_properties_length:
        props_str = props_str[:max_properties_length] + '...'
    # Construct and return the result string with all unique and truncated properties
    return f'(input GeoJSON properties: {props_str})'


def get_analytics_prompt(
        sentences: list[str],
        indicator_description: str,
        bio: str,
        lang: str,
        selected_area_geojson: dict,
        reference_area_geojson: dict,
) -> str:
    '''compose prompt to recieve analytics for provided axes'''
    reference_area_props = get_properties(reference_area_geojson)
    selected_area_props = get_properties(selected_area_geojson)
    LOGGER.debug('reference_area geom is %s', 'not empty' if reference_area_geojson else 'empty')
    LOGGER.debug('selected_area geom is %s', 'not empty' if selected_area_geojson else 'empty')
    prompt_start = f'Selected area properties: {selected_area_props}'

    if reference_area_geojson == selected_area_geojson:
        # compare selected_area only with world
        reference_area_geojson = None

    if reference_area_geojson:
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
