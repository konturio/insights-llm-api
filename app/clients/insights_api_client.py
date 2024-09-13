from datetime import datetime, timedelta

import ujson as json
from starlette.exceptions import HTTPException
from aiohttp import ClientSession

from app.settings import Settings
from app.logger import LOGGER

settings = Settings()

indicators_graphql = """
{
  polygonStatistic (polygonStatisticRequest: {polygon: "%s"})
  {
      bivariateStatistic{indicators{name, label, description, emoji, unit{longName}}}
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
            resolution,
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

axis_graphql = """
{
    getAxes {
        axis{
            label
            datasetStats{
                minValue,
                maxValue,
                mean,
                stddev
            }
            quality
            quotients {
                name
                label
                emoji
                description
                copyrights
                direction
                unit {
                    id
                    shortName
                    longName
                }
            }
            transformation {
                transformation
                min
                mean
                stddev
                lowerBound
                upperBound
                skew
            }
        }
    }
}
"""


async def get_axes() -> str:
    headers = {
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        axes = await query_insights_api(session, axis_graphql)
        LOGGER.debug('got axes')
        return axes


def get_analytics_resolution(data: dict) -> int:
    '''
    currently resolution is the same for all axes in analytics.
    return resolution of first entry just for debug
    '''
    for item in data['data']['polygonStatistic']['analytics']['advancedAnalytics']:
        return item['resolution']


async def get_analytics_sentences(selected_area: dict, reference_area: dict) -> tuple[list[str], str]:
    '''
    accepts selected_area and reference_area as geojson.
    returns tuple:
        - textual description of indicators stats for selected_area compared to world and reference_area
        - descriptions of indicators used in stats
    '''
    headers = {
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        analytics_selected_area = await query_insights_api(session, advanced_analytics_graphql, selected_area)
        LOGGER.debug('got selected_area analytics with resolution %s', get_analytics_resolution(analytics_selected_area))
        analytics_reference_area = {}
        if reference_area:
            analytics_reference_area = await query_insights_api(session, advanced_analytics_graphql, reference_area)
            LOGGER.debug('got reference_area analytics with resolution %s', get_analytics_resolution(analytics_reference_area))
        analytics_world = await query_insights_api(session, advanced_analytics_graphql)
        LOGGER.debug('got world analytics')
        metadata = await query_insights_api(session, indicators_graphql)
        LOGGER.debug('got indicators metadata')

    metadata = {
        x['name']: {
            'unit': x['unit']['longName'],
            'emoji': x['emoji'],
            'label': x['label'],
            'description': x['description'],
        }
        for x in metadata['data']['polygonStatistic']['bivariateStatistic']['indicators']
    }
    calculations_world = flatten_analytics(analytics_world, metadata)
    calculations_selected_area = flatten_analytics(analytics_selected_area, metadata)
    calculations_reference_area = flatten_analytics(analytics_reference_area, metadata) if reference_area else {}
    sorted_calculations = get_sorted_area_stats(calculations_world, calculations_selected_area, calculations_reference_area)

    # select descriptions of indicators that got included in sorted_calculations
    descriptions = {
        metadata[x['numerator']]['label']: metadata[x['numerator']]['description']
        for x in sorted_calculations
    }
    descriptions_txt = '''
        Here are descriptions for indicators:
    ''' + ';\n'.join(f'{k}: {v}' for k, v in descriptions.items() if v)

    return to_readable_sentence(sorted_calculations, calculations_world, calculations_reference_area), descriptions_txt


async def query_insights_api(session: ClientSession, query: str, geojson=None) -> dict:
    '''
    send graphql query to insights-api service for provided geojson
    '''
    if '%s' in query:
        # that means query requires polygon as parameter
        geojson = json.dumps(geojson) if geojson else '{"type":"FeatureCollection","features":[]}'
        query = query.format(polygon=geojson.replace('\\', '\\\\').replace('"','\\"'))
        #LOGGER.debug(query)
    async with session.post(settings.INSIGHTS_API_URL, json={'query': query}) as resp:
        if resp.status != 200:
            raise HTTPException(status_code=resp.status)
        data = await resp.json()
        if errors := data.get('errors'):
            LOGGER.error('error in insights-api response: %s', str(errors))
            raise HTTPException(status_code=400)
        return data


def flatten_analytics(data: dict, metadata: dict) -> dict[tuple, dict]:
    '''
    flatten advancedAnalytics response for the world or selected area, add units & emoji
    and return a dict (calculation, numerator, denominator) -> {calc_data}
    '''

    calculations_world = {}
    for item in data['data']['polygonStatistic']['analytics']['advancedAnalytics']:
        numerator = item['numerator']
        if numerator not in metadata:
            # indicator not ready yet
            continue

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
            if metadata[numerator]['unit'] == 'date':
                if calculation == 'sum':
                    # timestamp addition makes no sense
                    continue

                if denominatorLabel != '1':
                    # timestamp divided by area or population makes no sense
                    continue

            if item['denominatorLabel'] == 'Area':
                if 'Man-days' in item['numeratorLabel'] or 'Man-distance' in item['numeratorLabel']:
                    # layers of low interpretability and strange dimensionality (ppl/km, ppl*day/km2)
                    continue

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
                'emoji': metadata[numerator]['emoji'],
                'numeratorUnit': metadata[numerator]['unit'],
                'denominatorUnit': metadata[denominator]['unit'],
            }
    return calculations_world


def calc_sigma(calculations: dict, ref: dict, world: dict, key: tuple) -> float:
    '''
    Calculate the sigma value for the 'mean' calculation type.

    Sigma is computed as the absolute difference between the mean values from
    two different polygons, divided by the standard deviation. This results in
    a dimensionless value that can be used for sorting different types of measurements
    '''
    stddev_key = 'stddev', *key[1:]
    if key[0] != 'mean' or key not in ref or stddev_key not in world:
        return 0

    return abs(
        (calculations['value'] - ref[key]["value"]) /
        world[stddev_key]["value"]
    )


def get_sorted_area_stats(
        calculations_world: dict[tuple, dict],
        calculations_selected_area: dict[tuple, dict],
        calculations_reference_area: dict[tuple, dict],
) -> list[dict]:
    '''
    add sigma to area analytics compared to the world mean metric
    and return a list [{calc_data}] sorted by quality, sigma, numerator & value.
    max list size = MAX_ANALYTICS_SENTENCES
    '''
    for key, v in calculations_selected_area.items():
        v['world_sigma'] = calc_sigma(v, calculations_world, calculations_world, key)
        v['reference_area_sigma'] = calc_sigma(v, calculations_reference_area, calculations_world, key)

    # Sort the list of calculations by the absolute value of the quality in ascending order
    return sorted(calculations_selected_area.values(), key=lambda x: (
        int(abs(x['quality']) / 2) * 2,
        -x['reference_area_sigma'],  # <- will be the same for all rows if reference_area is None
        -x['world_sigma'],
        x['numerator'],
        x['value']
    ))[:settings.MAX_ANALYTICS_SENTENCES]


def unit_to_str(entry: dict, sigma=False):
    ''' possible units are:
            United States dollar (USD)
            date (unixtime)
            days
            degrees
            degrees Celsius
            fraction
            hours
            index
            kilometers
            meters
            meters per square second
            number
            people
            square kilometers
            watt per square metre
            watts per square centimeter per steradian
    '''

    if sigma:
        return ''

    if entry['denominatorLabel'] == 'Population':
        if 'Man-distance' in entry['numeratorLabel']:
            # man-distance has dimensionality ppl*km. ppl*km / ppl == km
            return ' kilometers'
        if 'Man-days' in entry['numeratorLabel']:
            # man-days has dimensionality ppl*days
            return ' days'

    if (entry['denominatorUnit'] == entry['numeratorUnit'] or
            entry['numeratorUnit'] in ('index', None, 'fraction') or
            (entry['numeratorUnit'] == 'number' and entry['denominatorLabel'] == '1')):
        return ''

    s = entry['numeratorUnit'].replace('number', '') or ''
    if entry['denominatorUnit'] and entry['denominatorLabel'] != '1':
        s += ' per ' + (entry['denominatorUnit']
                .replace('people', 'person')
                .replace('square kilometers', 'square kilometer'))
    if s and s[0] != ' ':
        s = ' ' + s
    return s


def value_to_str(x: float, entry: dict, sigma=False):
    if x is None:
        return ''

    if (not sigma
            and entry['numeratorUnit'] == 'date'
            and entry['denominatorLabel'] == '1'
            and x < 2000000000):
        if entry['calculation'] == 'stddev':
            return str(timedelta(seconds=int(x)))
        return datetime.fromtimestamp(int(x)).isoformat()

    unit_str = unit_to_str(entry, sigma)
    # Format the value to be more readable, especially handling scientific notation.
    return (f'{x:,.2f}' if x > 1e-3 else f'{x:.2e}') + unit_str


def to_readable_sentence(
        selected_area_data: list[dict],
        world_data: dict[tuple, dict],
        reference_area_data: dict[tuple, dict] = None,
) -> list[str]:
    '''
    compose a list of readable sentences that describe analytics
    for selected_area, world and reference_area
    '''
    readable_sentences = []
    prev_axis = None

    # selected_area_data is sorted by importance
    for entry in selected_area_data:
        numerator_label = entry['numeratorLabel']
        if entry['emoji']:
            numerator_label = entry['emoji'] + ' ' + numerator_label

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

        if prev_axis == f'{numerator_label}{denominator_label}':
            sentence = f', {calculation_type} is {value_str}{reference_area_str}{world_str}'
            readable_sentences[-1] += sentence
        else:
            readable_sentences.append(sentence)

        prev_axis = f'{numerator_label}{denominator_label}'

    return readable_sentences
