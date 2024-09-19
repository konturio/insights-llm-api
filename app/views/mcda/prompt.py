from .examples import solar_farms_example


async def get_mcda_prompt(query, bio, axis_data) -> str:
    ''' MCDA Wizard assistant knows termonilogy and has instructions on what to do with axis data '''
    return '''
        {axis_and_indicators_description}

        ## Example of how to provide the indicators for some user request

        Request: """Best place to put solar farms"""

        Response: """
            {solar_farms_example}
        """

        ## Detailed explanation of the task

        Complete the task following the next steps.

        ### Step 1: Pick 2..6 indicators that will help to perform geospatial analysis requested by user

        The user's request is: """{user_query}""".
        When analyzing the user's query, first check if the request is meaningful. If the request appears to be random, or does not make sense as a valid request (e.g., gibberish or accidental typing), do not respond with an analysis. Instead, respond with {{"error": <reason why the input doesn't seem relevant or valid for analysis>}}. If the input is valid, proceed as usual.

        Use the user's bio "{user_bio}" to personalize the analysis and add contextual insights that might enhance the analysis. Focus on the request """{user_query}""", do not shift the main focus away from it and leverage bio details only if applicable. 

        Rules for selecting indicators:

        1. Identify indicators that directly measure or are significantly impacted by the user's specific request, rather than those that are proxies or indirectly related.
        2. Start with most important indicators.
        3. Avoid using more than 6 layers in the analysis.
        4. When adding new indicator to the analysis, check if you've already chosen some layers that are similar or overlap in meaning. Identify and select the most suitable one that best represents the intended analysis, rather than including all similar layers.  Each chosen layer should add distinct and valuable insights to the analysis. For example, population density and proximity to populated areas are interchangable: they both measure population density in different ways, it's redundant to include both.
        6. Reevaluate the chosen indicators to ensure they align with """{user_query}""" request, rather than the consequences or secondary effects.
        5. Explain your picks in "comment" field. Provide brief explanations for each selected layer, directly linking it to the user's request.  

        ### Step 2: create a name for analysis

        The name can be the same as user's request if it's comprehensive enough.
        Alternatively, you may paraphrase user's request to be more descriptive and contextual if needed.
        Analysis name will be displayed on UI as a label for the analysis you're creating.

        ### Step 3: evaluate indicators

        You need to evaluate an indicator's value as good or bad for the specific analysis being performed, tell whether higher or lower values of an indicator are desirable in the context of the user's request.
        Evaluation can be either "lower values are better" or "higher values are better". Set your evaluation to "indicator_evaluation" field.

        #### Algorithm for indicator evaluation:

        1. If the indicator's higher value represents a positive or desirable condition:
            - choose "indicator_evaluation": "higher values are better"
            - meaning: Higher indicator values are beneficial or preferred; lower values are less desirable. This evaluation is set when higher values contribute positively to the analysis outcome.
        2. If the indicator's lower value represents a positive or desirable condition:
            - choose "indicator_evaluation": "lower values are better"
            - meaning: Lower indicator values are beneficial or preferred; higher values are less desirable. This evaluation is set when lower values contribute positively to the analysis outcome.

        Example 1: you've selected "Population (ppl/km²)" as one of axes for analysis. Is high population density is better than low for current analysis? set "higher values are better".
        Example 2: you've selected "Proximity to X". Proximity is usually measured in m or km, it's literally distance. Higher values represent greater distance, lower values are smaller distance. So if closer distance (lower proximity values) is more beneficial, evaluation should be "lower values are better".

        Explain evaluation in "evaluation_hint" field: why the particular option is selected, how it follows the Algorithm for indicator evaluation.

        ### Step 4: create a json containing indicators selected for analysis

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
            + ' This indicator is valid for non-populated areas between cities' if x['quotients'][0]['name'] == 'populated_areas_proximity_m' else ''
        for x in axis_data['data']['getAxes']['axis']
        if x['quotients'][0]['description']
    )
    return '''
        ## System datasets

        Axis is a tuple numerator/denominator where both numerator and denominator are geospatial indicators (datasets) available in the system.
        List of available axes: """
            {axes}
        """

        Here are descriptions for indicators (numerators and denominators) that are included in axes: """
            {indicators}
        """
    '''.format(
        axes='\n'.join(str(a) for a in axes),
        indicators=';\n'.join(sorted(indicator_descriptions)),
    )
