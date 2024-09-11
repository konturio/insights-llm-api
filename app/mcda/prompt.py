from app.clients.insights_api_client import get_axes
from .examples import solar_farms_example


async def get_mcda_prompt(query, bio) -> str:
    ''' MCDA Wizard assistant knows termonilogy and has instructions on what to do with axis data '''
    axis_data = await get_axes()
    return '''
        {axis_description}
        Here is the example of how to provide the indicators. 

        Request:
            Best place to put solar farms

        Response:
            {solar_farms_example}

        User wrote in their bio: "{user_bio}". The main task is to provide an analysis for the user's query: "{user_query}". Use the bio only to add contextual insights that might personalize or enhance the analysis, but do not shift the main focus away from the query "{user_query}".
    '''.format(
        axis_description=get_axis_description(axis_data),
        solar_farms_example=solar_farms_example,
        user_bio=bio,
        user_query=query,
    )
    #txt += f'''
    #    User wrote in their bio: "{bio}". This is not the main request, but take this info into account,
    #    as it may include user's preferences for analytics, occupation and interest in geospatial analysis.
    #    User requested analysis for this query: "{query}"
    #'''
    ##TODO explain bio, min max sttdev
    return txt


def get_axis_description(axis_data: dict) -> str:
    axes = [
        {
            'axis_name': x['label'],
            'min': x['datasetStats']['minValue'],
            'max': x['datasetStats']['maxValue'],
    #        'mean': x['datasetStats']['mean'],
    #        'stddev': x['datasetStats']['stddev'],
            'numerator': {
                'name': x['quotients'][0]['name'],
                'label': (x['quotients'][0]['emoji'] or '') + ' ' + x['quotients'][0]['label'],
    #            'unit': x['quotients'][0]['unit']['longName'],
            },
            'denominator': {
                'label': x['quotients'][1]['label'],
            },
        }
        for x in sorted(axis_data['data']['getAxes']['axis'], key=lambda a: a['quality'] or 0, reverse=True)
        if x['quality'] and x['quality'] > 0.5
    ]

    indicator_descriptions = frozenset(
        (x['quotients'][0]['emoji'] or '') + ' ' + x['quotients'][0]['label'] + ': ' +
        x['quotients'][0]['description']
        for x in axis_data['data']['getAxes']['axis']
        if x['quotients'][0]['description']
    )
    descriptions_txt = '''
        Here are descriptions for indicators:
    ''' + ';\n'.join(sorted(indicator_descriptions))
    return '''
        List of indicators that are available in the system is provided below.
    ''' + '\n'.join(str(a) for a in axes) + descriptions_txt
