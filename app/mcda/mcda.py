import ujson as json

from app.clients.openai_client import OpenAIClient
from app.settings import Settings
from .prompt import get_mcda_prompt

settings = Settings()


async def get_mcda_suggestion(query, bio) -> dict:
    prompt = await get_mcda_prompt(query, bio)
    openai_client = OpenAIClient(assistant_name=settings.OPENAI_MCDA_ASSISTANT)
    llm_response = await openai_client.get_cached_llm_commentary(prompt)
    #TODO complete MCDA format
    return make_valid_mcda(llm_response)


def make_valid_mcda(x):
    return json.loads(x)
    # TODO: чтобы не запрашивать ещё раз инсайтс, можно заранее скачать всё, что нужно для MCDA: в т.ч. копирайты, трансформации и даже точки к ним. скачать, сохранить вначале и дотянуть досюда
    # TODO2: чтобы учитывать изменения инструкций в кэше, лучше бы их в промпт притянуть
