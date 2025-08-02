from .examples import solar_farms_example, cropland_burn_risk_example


async def get_mcda_prompt(query, bio, axis_data) -> str:
    '''MCDA Wizard assistant knows terminology and has instructions on what to do with axis data.'''
    return '''
        {axis_and_indicators_description}

        ## Example of how to provide the indicators for some user request

        Request: """Best place to put solar farms"""

        Response: """
            {solar_farms_example}
        """

        Request: """Cropland burn risk"""

        Response: """
            {cropland_burn_risk_example}
        """

        ## Detailed explanation of the task

        Complete the task following the next steps.

        ### Step 1: Pick 2..4 indicators that will help to perform geospatial analysis requested by user

        The user's request is: """{user_query}""".
        When analyzing the user's query, first check if the request is meaningful. If the request appears to be random, or does not make sense as a valid request (e.g., gibberish or accidental typing), do not respond with an analysis. Instead, respond with {{"error": <reason why the input doesn't seem relevant or valid for analysis>}}. If the input is valid, proceed as usual.

        Use the user's bio "{user_bio}" to prioritize indicators that align with the user's lifestyle or preferences. When the user's query is vague, the bio (if present) can provide clues about their priorities or concerns. But focus on the request """{user_query}""", do not shift the main focus away from it and leverage bio details only if applicable. 

        Rules for selecting indicators:

        - Select the most relevant indicators for the map analysis of the user's query "{user_query}".
        - Identify indicators that directly measure or are significantly impacted by the user's specific request, rather than those that are proxies or indirectly related.
        - Start with most important indicators.
        - Include the subject of analysis into the indicators list. e.g. Forest area for forest analysis, Hotels for hotel analysis.
        - Avoid using more than 4 layers in the analysis.
        - Do not include the same indicator twice.
        - Each indicator should add distinct and valuable insights to the analysis. Skip adding similar ones. e.g. population density and proximity to populated areas are interchangeable: they both measure population density in different ways, it's redundant to include both.
        - When indicators get colored, the map gets unreadable, because indicators similar in meaning reduce contrast. Do not include indicators capturing the same risk. Avoid pairing "Number of days under cyclone impact, last year (n) (days)" with "Tropical Cyclone hazard (index)", or combining "Hazard & Exposure" layers with any "Number of days under X" layer, because they capture the same risk and provide overlapping insights. When deciding between similar indicators, explain your choice in comment.
        - Diversity of insights and avoidance of duplicate perspectives within a category of risk is crucial – pick diverse indicators.
        - Ensure that indicators align with """{user_query}""" request, rather than the consequences or secondary effects.
        - Explain your picks in "comment" field. Provide brief explanations for each selected layer, directly linking it to the user's request.
        - Indicators are provided with multiple normalization options (by area, by population, by roads, etc). Select only relevant normalization.
        - Use layerSpatialRes to match the scale of the user's question: "where on the planet" can rely on admin_national layers, "in which city of the country" requires at least admin_subnational or grid_coarse, "where in the city" demands feature_derived or grid_fine. You may select more detailed layers but never less detailed ones.
        - Keep in mind layerTemporalExt, some indicators cover only a specific time range.

        ### Step 2: create a name for analysis

        The name can be the same as user's request if it's comprehensive enough.
        Alternatively, you may paraphrase user's request to be more descriptive and contextual if needed.
        Analysis name will be displayed on UI as a label for the analysis you're creating.

        ### Step 3: evaluate indicators

        You need to evaluate an indicator's value axis as good or bad for the specific analysis being performed, tell whether higher or lower values of an indicator are desirable in the context of the user's request.
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
        cropland_burn_risk_example=cropland_burn_risk_example,
        user_bio=bio,
        user_query=query,
    )
    # min, max and stddev values describe an indicator's distribution and help
    # tune visualization scales.


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
            'description': x['quotients'][0]['description'],
            'layerSpatialRes': x['quotients'][0]['layerSpatialRes'],
            'layerTemporalExt': x['quotients'][0]['layerTemporalExt'],
        }
        for x in sorted(axis_data['data']['getAxes']['axis'], key=lambda a: a['quality'] or 0, reverse=True)
        if (x['quality'] and x['quality'] > 0.5
                and x['quotients'][1]['name'] != 'populated_area_km2')  # weird denominator, area_km2 replaces it for any analysis
    ]

    layer_spatial_res_table = '''
        |value|meaning|
        |---|---|
        |admin_national|one value per country (ISO 3166-1 boundary)|
        |admin_subnational|any aggregated admin unit below the country level (admin-1, admin-2, counties, districts…)|
        |grid_coarse|regularly-spaced rasters or H3 > ≈1 km (250 m GHS-POP counts as coarse once aggregated)|
        |grid_fine|rasters or H3 ≤ ≈1 km (250 m, 100 m, 30 m, etc.)|
        |feature_derived|counts, densities or proximities based on discrete features (points, lines, polygons)|
    '''

    layer_temporal_ext_table = '''
        |value|meaning|
        |---|---|
        |static|fixed value; doesn’t move with the calendar|
        |historical_static|fixed multi-year climatology or census baseline compiled >10 years ago; doesn’t move with the calendar|
        |snapshot_year|a single named year (often last authoritative release)|
        |rolling_2_years|moving 2-year window ending “today”|
        |rolling_year|moving 365-day window ending “today”|
        |rolling_6_months|moving 6-month (or 183-day) window|
        |rolling_month|moving 30-day (or 4-week) window|
        |current_value|latest single measurement, updated continuously|
        |cumulative_to_date|running total from the first record up to now; only increases (or steps down on data corrections)|
        |future_projection|any modelled future scenario (RCP, SSP, +2 °C, 2050-forecast)|
    '''

    return '''
        ## System datasets

        Axis is a tuple numerator/denominator where both numerator and denominator are geospatial indicators (datasets) available in the system.
        List of available axes: """
            {axes}
        """

        layerSpatialRes values:
        {layer_spatial_res_table}

        layerTemporalExt values:
        {layer_temporal_ext_table}

        Note that "Proximity to X" indicators are usually measured in m or km, it's literally distance. Higher values represent greater distance, lower values are smaller distance.
    '''.format(
        axes='\n'.join(str(a) for a in axes),
        layer_spatial_res_table=layer_spatial_res_table,
        layer_temporal_ext_table=layer_temporal_ext_table,
    )
