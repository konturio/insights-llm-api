from app.clients.insights_api_client import get_axes
from .examples import solar_farms_example


async def get_mcda_prompt(query, bio) -> str:
    ''' MCDA Wizard assistant knows termonilogy and has instructions on what to do with axis data '''
    axis_data = await get_axes()
    txt = get_axis_description(axis_data)
    txt += '''
        Here is the example of how to provide the indicators. 

        Request:
            Best place to put solar farms

        Response:
    '''
    txt += solar_farms_example

    txt += f'''
        User wrote in their bio: "{bio}"
        User requested analysis for this query: "{query}"
    '''
    #TODO explain bio, min max sttdev
    print(txt)
    return txt


def get_axis_description(axis_data: dict) -> str:
    axes = [
        {
            'axis_name': x['label'],
            'min': x['datasetStats']['minValue'],
            'max': x['datasetStats']['maxValue'],
            'mean': x['datasetStats']['mean'],
            'stddev': x['datasetStats']['stddev'],
            'numerator': {
                'name': x['quotients'][0]['name'],
                'label': x['quotients'][0]['emoji'] + ' ' + x['quotients'][0]['label'],
                'unit': x['quotients'][0]['unit']['longName'],
            },
            'denominator': {
                'label': x['quotients'][1]['emoji'] + ' ' + x['quotients'][1]['label'],
            },
        }
        for x in axis_data['data']['getAxes']['axis']
        if x['quality'] > 0.5
    ]

    indicator_descriptions = frozenset(
        x['quotients'][0]['emoji'] + ' ' + x['quotients'][0]['label'] + ': ' +
        x['quotients'][0]['description']
        for x in axis_data['data']['getAxes']['axis']
        if x['quotients'][0]['description']
    )
    descriptions_txt = '''
        Here are descriptions for indicators:
    ''' + ';\n'.join(indicator_descriptions)
    return '''
        List of indicators that are available in the system is provided below.
    ''' + '\n'.join(str(a) for a in axes) + descriptions_txt
