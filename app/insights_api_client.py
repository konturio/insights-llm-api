from datetime import datetime

import ujson as json
from starlette.exceptions import HTTPException
from aiohttp import ClientSession

from settings import Settings
from logger import LOGGER

settings = Settings()

graphql = """
{
  polygonStatistic (polygonStatisticRequest: {polygon: "%s"})
  {
    analytics {
        advancedAnalytics {
            numerator,
            denominator,
            numeratorLabel,
            denominatorLabel,
            analytics {
                value,
                calculation,
                quality
            }
        }
    }
  }
}
"""


async def get_analytics_sentences(selected_area: dict, aoi: dict = None) -> list[str]:
    '''
    accepts selected_area and aoi as geojson.
    returns textual description of indicators stats for selected_area compared to world and AOI
    '''
    headers = {
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        analytics_selected_area = await get_analytics_from_insights_api(session, selected_area)
        # TODO 18291: analytics_aoi = await get_analytics_from_insights_api(session, aoi))
        analytics_world = await get_analytics_from_insights_api(session)

    calculations_world = get_world_stats(analytics_world)
    sorted_calculations = get_area_stats(calculations_world, analytics_selected_area)
    return to_readable_sentence(sorted_calculations, calculations_world)


async def get_analytics_from_insights_api(session: ClientSession, geojson=None) -> dict:
    '''
    send advancedAnalytics graphql query to insights-api service for provided geojson
    '''
    geojson = json.dumps(geojson) if geojson else '{"type":"FeatureCollection","features":[]}'
    query = graphql % geojson.replace('"','\\"')
    #print(query)
    async with session.post(settings.INSIGHTS_API_URL, json={'query': query}) as resp:
        if resp.status != 200:
            raise HTTPException(status_code=resp.status)
        data = await resp.json()
        if errors := data.get('errors'):
            LOGGER.error('error in insights-api response: %s', str(errors))
            raise HTTPException(status_code=400)
        return data


def get_world_stats(data: dict) -> dict[tuple, dict]:
    '''
    flatten advancedAnalytics response for the world
    and create a dict (calculation, numerator, denominator) -> {calc_data}
    '''
    calculations_world = {}
    for item in data['data']['polygonStatistic']['analytics']['advancedAnalytics']:
        numerator = item['numerator']
        denominator = item['denominator']
        numeratorLabel = item['numeratorLabel']
        denominatorLabel = item['denominatorLabel']

        # Iterate over each 'analytics' entry and add a dictionary for each calculation to the list
        for analytic in item['analytics']:
            calculation = analytic['calculation']
            if 'value' in analytic:
                value = analytic['value']
                quality = analytic['quality']
                calculations_world[(calculation, numerator, denominator)] = {
                    'numerator': numerator,
                    'denominator': denominator,
                    'numeratorLabel': numeratorLabel,
                    'denominatorLabel': denominatorLabel,
                    'calculation': calculation,
                    'value': value,
                    'quality': quality
                }
    return calculations_world


def get_area_stats(calculations_world: dict[tuple, dict], data: dict) -> list[dict]:
    '''
    flatten advancedAnalytics response for the polygon (AOI or selected area)
    and create a list [{calc_data}] sorted by quality, sigma, numerator & value
    '''
    calculations = []
    for item in data['data']['polygonStatistic']['analytics']['advancedAnalytics']:
        numerator = item['numerator']
        denominator = item['denominator']
        numeratorLabel = item['numeratorLabel']
        denominatorLabel = item['denominatorLabel']

        for analytic in item['analytics']:
            calculation = analytic['calculation']
            if analytic.get('value') is not None:
                value = analytic['value']
                quality = analytic['quality']
                world_key = (calculation, numerator, denominator)
                sigma = 0
                if world_key in calculations_world and calculation == 'mean':
                    sigma = abs(
                        (value - calculations_world[world_key]["value"]) /
                        calculations_world[("stddev", numerator, denominator)]["value"]
                    )
                calculations.append({
                    'numerator': numerator,
                    'denominator': denominator,
                    'numeratorLabel': numeratorLabel,
                    'denominatorLabel': denominatorLabel,
                    'calculation': calculation,
                    'value': value,
                    'quality': quality,
                    'sigma': sigma
                })

    # Sort the list of calculations by the absolute value of the quality in ascending order
    return sorted(calculations, key=lambda x: (
        int(abs(x['quality'])), -x['sigma'], x['numerator'], x['value']
    ))


def to_readable_sentence(selected_area_data: list[dict], world_data: dict[tuple, dict], aoi_data=None) -> list[str]:
    '''
    compose a list of readable sentences that describe analytics for selected_area, world and aoi
    '''
    readable_sentences = []

    for entry in selected_area_data:
        numerator_label = entry['numeratorLabel']
        if numerator_label == "Population (previous version)":
            continue
        
        if entry['denominatorLabel'] == "Area":
            entry['denominatorLabel'] = "area km2"
        denominator_label = " over " + entry['denominatorLabel']
        if entry['denominatorLabel'] == "1":
            denominator_label = ""
        calculation_type = entry['calculation'] #.capitalize()
        value = entry['value']
        quality = entry['quality']
        
        world_key = (entry['calculation'], entry['numerator'], entry['denominator'])
        world_value = ""
        if world_key in world_data and world_data[world_key]["value"] is not None:
            world_value = world_data[world_key]["value"]
            world_value_formatted = (f"{world_value:.2f}" if world_value > 1e-3 else f"{world_value:.2e}")
            
            if (entry['numeratorLabel'] in ("OSM: last edit", "OSM: first edit", "OSM: last edit (avg)")
                    and entry['denominatorLabel'] == "1"
                    and world_value < 2000000000):
                world_value_formatted = datetime.fromtimestamp(int(world_data[world_key]["value"])).isoformat()
            
            world_value = " (globally "+ world_value_formatted+ ")"
            quality = (quality + world_data[world_key]["quality"])/2

        # Format the value and quality to be more readable, especially handling scientific notation.
        value_str = f"{value:.2f}" if value > 1e-3 else f"{value:.2e}"
        
        sigma_str = ""
        if entry["sigma"]:
            sigma_str = " ("+ (f"{value:.2f}" if value > 1e-3 else f"{value:.2e}") +" sigma)"
        
        if (entry['numeratorLabel'] in ("OSM: last edit", "OSM: first edit", "OSM: last edit (avg)")
                and entry['denominatorLabel'] == "1" 
                and value < 2000000000):
            value_str = datetime.fromtimestamp(int(value)).isoformat()
        
        #quality_str = f"{abs(quality):.2f}"
        
        sentence = (
            f"{calculation_type} of {numerator_label}{denominator_label} is {value_str}{world_value}{sigma_str}"
            #f"with a quality metric of {quality_str}."
        )
        # example: mean of Air temperature (min) is 15.73 (globally 1.03) (15.73 sigma)
        # TODO: add AOI values if exists
        readable_sentences.append(sentence)

    return readable_sentences
