from datetime import datetime, timedelta

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


async def get_analytics_sentences(selected_area: dict, reference_area: dict) -> list[str]:
    '''
    accepts selected_area and reference_area as geojson.
    returns textual description of indicators stats for selected_area compared to world and reference_area
    '''
    headers = {
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        analytics_selected_area = await query_insights_api(session, advanced_analytics_graphql, selected_area)
        analytics_reference_area = {}
        if reference_area:
            analytics_reference_area = await query_insights_api(session, advanced_analytics_graphql, reference_area)
        analytics_world = await query_insights_api(session, advanced_analytics_graphql)
        units = await query_insights_api(session, indicators_graphql)

    calculations_world = flatten_analytics(analytics_world, units)
    calculations_selected_area = flatten_analytics(analytics_selected_area, units)
    calculations_reference_area = flatten_analytics(analytics_reference_area, units) if reference_area else {}
    sorted_calculations = get_sorted_area_stats(calculations_world, calculations_selected_area, calculations_reference_area)

    return to_readable_sentence(sorted_calculations, calculations_world, calculations_reference_area, units)


async def query_insights_api(session: ClientSession, graphql: str, geojson=None) -> dict:
    '''
    send graphql query to insights-api service for provided geojson
    '''
    geojson = json.dumps(geojson) if geojson else '{"type":"FeatureCollection","features":[]}'
    query = graphql % geojson.replace('"','\\"')
    #LOGGER.debug(query)
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
    flatten advancedAnalytics response for the world or selected area, add units
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


def calc_sigma(calculations: dict, ref: dict, key: tuple) -> float:
    '''
    return sigma only for 'mean' calculation
    '''
    stddev_key = 'stddev', *key[1:]
    if key[0] != 'mean' or key not in ref or stddev_key not in ref:
        return 0

    return abs(
        (calculations['value'] - ref[key]["value"]) /
        ref[stddev_key]["value"]
    )


def get_sorted_area_stats(
        calculations_world: dict[tuple, dict],
        calculations_selected_area: dict[tuple, dict],
        calculations_reference_area: dict[tuple, dict],
) -> list[dict]:
    '''
    add sigma to area analytics compared to the world mean metric
    and return a list [{calc_data}] sorted by quality, sigma, numerator & value
    '''
    for key, v in calculations_selected_area.items():
        v['world_sigma'] = calc_sigma(v, calculations_world, key)
        v['reference_area_sigma'] = calc_sigma(v, calculations_reference_area, key)

    # Sort the list of calculations by the absolute value of the quality in ascending order
    return sorted(calculations_selected_area.values(), key=lambda x: (
        int(abs(x['quality'])),
        *((-x['reference_area_sigma'], -x['world_sigma']) if calculations_reference_area else (-x['world_sigma'],)),
        x['numerator'],
        x['value']
    ))


def value_to_str(x: float, entry: dict, sigma=False):
    if x is None:
        return ''

    if (entry['numeratorUnit'] == 'unixtime'
            and entry['denominatorLabel'] == '1'
            and x < 2000000000):
        if sigma:
            return str(timedelta(seconds=int(x)))
        return datetime.fromtimestamp(int(x)).isoformat()

    # Format the value to be more readable, especially handling scientific notation.
    return f'{x:.2f}' if x > 1e-3 else f'{x:.2e}'


def to_readable_sentence(
        selected_area_data: list[dict],
        world_data: dict[tuple, dict],
        reference_area_data: dict[tuple, dict] = None,
        units: dict = None,
) -> list[str]:
    '''
    compose a list of readable sentences that describe analytics
    for selected_area, world and reference_area (Area Of Interest)
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
        value_str = value_to_str(value, entry)

        key = entry['calculation'], entry['numerator'], entry['denominator']

        # compare with world
        world_value = world_data.get(key, {}).get('value')
        world_value_formatted = value_to_str(world_value, entry)
        world_sigma_str = ""
        if entry["world_sigma"]:
            world_sigma_str = ', ' + value_to_str(entry['world_sigma'], entry, sigma=True) + ' sigma'
        world_str = f' (globally {world_value_formatted}{world_sigma_str})' if world_value_formatted else ''

        # compare with reference_area
        reference_area_value = (reference_area_data or {}).get(key, {}).get('value')
        reference_area_value_formatted = value_to_str(reference_area_value, entry)
        reference_area_sigma_str = ""
        if entry["reference_area_sigma"]:
            reference_area_sigma_str = ', ' + value_to_str(entry['reference_area_sigma'], entry, sigma=True) + ' sigma'
        reference_area_str = f' (reference_area {reference_area_value_formatted}{reference_area_sigma_str})' if reference_area_value_formatted else ''

        #quality = entry['quality']
        #quality = (quality + world_data[key]["quality"])/2
        #quality_str = f"{abs(quality):.2f}"

        sentence = (
            f"{calculation_type} of {numerator_label}{denominator_label} is {value_str}{reference_area_str}{world_str}"
            #f"with a quality metric of {quality_str}."
        )
        # example: mean of Air temperature (min) is 15.73 (globally 1.03) (15.73 sigma)
        readable_sentences.append(sentence)

    return readable_sentences
