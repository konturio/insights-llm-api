from datetime import datetime

import ujson as json
from starlette.exceptions import HTTPException
from aiohttp import ClientSession

from .settings import Settings
from .logger import LOGGER

settings = Settings()

indicators_graphql = """
{
  polygonStatistic (polygonStatisticRequest: {polygon: "%s"})
  {
      bivariateStatistic{indicators{name, unit{id}}}
  }
}
"""

advanced_analytics_graphql = """
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
        analytics_selected_area = await query_insights_api(session, advanced_analytics_graphql, selected_area)
        # TODO 18291: analytics_aoi = await query_insights_api(session, advanced_analytics_graphql, aoi))
        analytics_world = await query_insights_api(session, advanced_analytics_graphql)
        units = await query_insights_api(session, indicators_graphql)

    calculations_world = flatten_analytics(analytics_world, units)
    calculations_area = flatten_analytics(analytics_selected_area, units)
    sorted_calculations = get_sorted_area_stats(calculations_world, calculations_area)

    return to_readable_sentence(sorted_calculations, calculations_world, units)


async def query_insights_api(session: ClientSession, graphql: str, geojson=None) -> dict:
    '''
    send graphql query to insights-api service for provided geojson
    '''
    geojson = json.dumps(geojson) if geojson else '{"type":"FeatureCollection","features":[]}'
    query = graphql % geojson.replace('"','\\"')
    LOGGER.debug(query)
    async with session.post(settings.INSIGHTS_API_URL, json={'query': query}) as resp:
        if resp.status != 200:
            raise HTTPException(status_code=resp.status)
        data = await resp.json()
        if errors := data.get('errors'):
            LOGGER.error('error in insights-api response: %s', str(errors))
            raise HTTPException(status_code=400)
        return data


def flatten_analytics(data: dict, units: dict) -> dict[tuple, dict]:
    '''
    flatten advancedAnalytics response for the world, add units
    and return a dict (calculation, numerator, denominator) -> {calc_data}
    '''
    units = {
        x['name']: x['unit']['id']
        for x in units['data']['polygonStatistic']['bivariateStatistic']['indicators']
    }
    # possible units are:
    # nW_cm2_sr None celc_deg km2 m days fract ppl deg m_s2 W_m2 h USD other n km unixtime index

    calculations_world = {}
    for item in data['data']['polygonStatistic']['analytics']['advancedAnalytics']:
        numerator = item['numerator']
        denominator = item['denominator']
        numeratorLabel = item['numeratorLabel']
        denominatorLabel = item['denominatorLabel']

        if numeratorLabel == "Population (previous version)":
            continue

        # Iterate over each 'analytics' entry and add a dictionary for each calculation to the list
        for analytic in item['analytics']:
            if analytic.get('value') is None:
                continue
            calculation = analytic['calculation']
            value = analytic['value']
            quality = analytic['quality']
            calculations_world[(calculation, numerator, denominator)] = {
                'numerator': numerator,
                'denominator': denominator,
                'numeratorLabel': numeratorLabel,
                'denominatorLabel': denominatorLabel,
                'calculation': calculation,
                'value': value,
                'quality': quality,
                'numeratorUnit': units[numerator],
                'denominatorUnit': units[denominator],
            }
    return calculations_world


def get_sorted_area_stats(calculations_world: dict[tuple, dict], calculations_area: dict[tuple, dict]) -> list[dict]:
    '''
    add sigma to area analytics compared to the world mean metric
    and return a list [{calc_data}] sorted by quality, sigma, numerator & value
    '''
    for world_key, v in calculations_area.items():
        calculation, numerator, denominator = world_key
        v['sigma'] = 0
        if calculation == 'mean' and world_key in calculations_world:
            v['sigma'] = abs(
                (v['value'] - calculations_world[world_key]["value"]) /
                calculations_world[("stddev", numerator, denominator)]["value"]
            )

    # Sort the list of calculations by the absolute value of the quality in ascending order
    return sorted(calculations_area.values(), key=lambda x: (
        int(abs(x['quality'])), -x['sigma'], x['numerator'], x['value']
    ))


def to_readable_sentence(selected_area_data: list[dict], world_data: dict[tuple, dict], aoi_data=None) -> list[str]:
    '''
    compose a list of readable sentences that describe analytics for selected_area, world and aoi
    '''
    readable_sentences = []

    for entry in selected_area_data:
        numerator_label = entry['numeratorLabel']
        
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
            
            if (entry['numeratorUnit'] == 'unixtime'
                    and entry['denominatorLabel'] == "1"
                    and world_value < 2000000000):
                world_value_formatted = datetime.fromtimestamp(int(world_data[world_key]["value"])).isoformat()
            
            world_value = " (globally "+ world_value_formatted+ ")"
            quality = (quality + world_data[world_key]["quality"])/2

        # Format the value and quality to be more readable, especially handling scientific notation.
        value_str = f"{value:.2f}" if value > 1e-3 else f"{value:.2e}"
        
        sigma_str = ""
        if entry["sigma"]:
            sigma_str = " ("+ (f"{entry['sigma']:.2f}" if entry["sigma"] > 1e-3 else f"{entry['sigma']:.2e}") +" sigma)"
        
        if (entry['numeratorUnit'] == 'unixtime'
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
