from .examples import solar_farms_example


async def get_mcda_prompt(query, bio, axis_data) -> str:
    ''' MCDA Wizard assistant knows termonilogy and has instructions on what to do with axis data '''
    return '''
        {axis_and_indicators_description}
        Here is the example of how to provide the indicators. 

        Request:
            Best place to put solar farms

        Response:
            {solar_farms_example}

        The user's request is: "{user_query}".
        When responding, you may paraphrase this request to be more descriptive and contextual if needed. This bill be displayed on UI as a label for your analysis you provide.
        Use the user's bio: "{user_bio}" to personalize the analysis and add contextual insights that might enhance the analysis. Focus on the request "{user_query}", do not shift the main focus away from it and leverage bio details only if applicable. 
    '''.format(
        axis_and_indicators_description=get_axis_description(axis_data),
        solar_farms_example=solar_farms_example,
        user_bio=bio,
        user_query=query,
    )
    # TODO explain min max sttdev
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
                'label': x['quotients'][0]['label'],
            },
            'denominator': {
                'name': x['quotients'][1]['name'],
            },
        }
        for x in sorted(axis_data['data']['getAxes']['axis'], key=lambda a: a['quality'] or 0, reverse=True)
        if x['quality'] and x['quality'] > 0.5
    ]

    indicator_descriptions = frozenset(
        x['quotients'][0]['label'] + ': ' +
        x['quotients'][0]['description']
        for x in axis_data['data']['getAxes']['axis']
        if x['quotients'][0]['description']
    )
    return '''
        Axis is a tuple numerator/denominator where both numerator and denominator are geospatial indicators (datasets) available in the system.
        List of available axes is provided below.
            {axes}

        Here are descriptions for indicators (numerators and denominators):
            {indicators}
    '''.format(
        axes='\n'.join(str(a) for a in axes),
        indicators=';\n'.join(sorted(indicator_descriptions)),
    )
