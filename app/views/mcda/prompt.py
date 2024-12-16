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

        Use the user's bio "{user_bio}" to prioritize indicators that align with the user's lifestyle or preferences. When the user's query is vague, the bio (if present) can provide clues about their priorities or concerns. But focus on the request """{user_query}""", do not shift the main focus away from it and leverage bio details only if applicable. 

        Rules for selecting indicators:

        1. Please try your best to select the most relevant indicators for the map analysis of the user's query "{user_query}".
        2. Identify indicators that directly measure or are significantly impacted by the user's specific request, rather than those that are proxies or indirectly related.
        3. Start with most important indicators.
        4. Avoid using more than 6 layers in the analysis.
        5. When adding new indicator to the analysis, check if you've already chosen some layers that are similar or overlap in meaning. Identify and select the most suitable one that best represents the intended analysis, rather than including all similar layers.  Each chosen layer should add distinct and valuable insights to the analysis. For example, population density and proximity to populated areas are interchangable: they both measure population density in different ways, it's redundant to include both.
        6. Do not include the same indicator twice.
        7. Reevaluate the chosen indicators to ensure they align with """{user_query}""" request, rather than the consequences or secondary effects.
        8. Explain your picks in "comment" field. Provide brief explanations for each selected layer, directly linking it to the user's request.  

        ### Step 2: create a name for analysis

        The name can be the same as user's request if it's comprehensive enough.
        Alternatively, you may paraphrase user's request to be more descriptive and contextual if needed.
        Analysis name will be displayed on UI as a label for the analysis you're creating.

        ### Step 3: evaluate indicators

        You need to evaluate an indicator's value as good or bad for the specific analysis being performed, tell whether higher or lower values of an indicator are desirable in the context of the user's request.
        Evaluation can be either "lower values are better" or "higher values are better". Set your evaluation to "indicator_evaluation" field.
        Explain evaluation in "evaluation_hint" field: why the particular option is selected, how it follows the Algorithm for indicator evaluation.

        #### Algorithm for indicator evaluation:

        1. For disaster risk and environmental impact assessment requests:
        - If higher indicator values indicate a higher risk or impact, choose "lower values are better", because low values => lower risk => low risk is desirable => lower values are better. Conversely, if lower values indicate a higher risk of the disaster, choose "higher values are better" (high values => lower risk => low risk is desirable => higher values are better).
        Example evaluation for landslide risk assesment:
        """
            "axis_name": "Slope (°)",
            "evaluation_hint": "Higher slope values indicate steeper terrain, which increases landslide risk.",
            "indicator_evaluation": "lower values are better"  # because low values = low risk = low risk is desirable
        """

        2. For site selection, suitability analysis and other requests:
        - If the indicator's higher value represents a positive or desirable condition, choose "indicator_evaluation": "higher values are better", meaning that higher indicator values are beneficial or preferred for user's request, and lower values are less desirable. "higher values are better" is set when higher values contribute positively to the analysis outcome. Otherwise set "lower values are better".
        Example evaluation for new wine shop placement:
        """
            "axis_name": "Hotels to populated area (n/km²)",
            "evaluation_hint": "Closer proximity to hotels is beneficial",
            "indicator_evaluation": "higher values are better"  # because high values = more benefits = more benefits is desirable
        """

        After reviewing these instructions thoroughly, select the most appropriate indicator_evaluation and explain your choices clearly. Be sure your first response aligns fully with these guidelines.

        ### Step 4: create a json containing indicators selected for analysis

    '''.format(
        axis_and_indicators_description=get_axis_description(axis_data),
        solar_farms_example=solar_farms_example,
        user_bio=bio,
        user_query=query,
    )
    # TODO explain min max sttdev


def get_axis_description(axis_data: dict) -> str:
    axes = [
        {
            'axis_name': x['label'],
            'min': x['datasetStats']['minValue'],
            'max': x['datasetStats']['maxValue'],
    #        'mean': x['datasetStats']['mean'],
    #        'stddev': x['datasetStats']['stddev'],
            'numerator': x['quotients'][0]['name'],
            'denominator': x['quotients'][1]['name'],
            'description': x['quotients'][0]['description']
                + ' This indicator is valid for non-populated areas between cities'
                        if x['quotients'][0]['name'] == 'populated_areas_proximity_m' else ''
                + ' Higher values indicate more peace and safety, low values imply ongoing conflicts and high militarization'
                        if x['quotients'][0]['name'] == 'safety_index' else ''
        }
        for x in sorted(axis_data['data']['getAxes']['axis'], key=lambda a: a['quality'] or 0, reverse=True)
        if (x['quality'] and x['quality'] > 0.5
                and x['quotients'][1]['name'] != 'populated_area_km2')  # weird denominator, area_km2 replaces it for any analysis
    ]

    return '''
        ## System datasets

        Axis is a tuple numerator/denominator where both numerator and denominator are geospatial indicators (datasets) available in the system.
        List of available axes: """
            {axes}
        """

        Note that "Proximity to X" indicators are usually measured in m or km, it's literally distance. Higher values represent greater distance, lower values are smaller distance.
    '''.format(
        axes='\n'.join(str(a) for a in axes),
    )
