solar_farms_example = '''{
    "original_request": "Best place to put solar farms",
    "analysis_name": "Best place to put solar farms",
    "axes": [
        {
            "comment": "Solar farms require sunlight",
            "axis_name": "Global Horizontal Irradiance (W/m²)",
            "min": 1,
            "max": 8,
            "numerator": "gsa_ghi",
            "denominator": "one",
            "evaluation_hint": "More sunlight = better performance = good, less sunlight = bad",
            "indicator_evaluation": "higher values are better"
        },
        {
            "comment": "Chopping down forest for solar farm is economically infeasible",
            "axis_name": "Forest landcover (km²/km²)",
            "min": 0,
            "max": 1,
            "numerator": "forest",
            "denominator": "area_km2",
            "evaluation_hint": "Places with no or less forest are better for solar farms",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "It is a bad idea to put solar farm in disaster-prone area",
            "axis_name": "All disaster types exposure (days)",
            "min": 0,
            "max": 365,
            "numerator": "hazardous_days_count",
            "denominator": "one",
            "evaluation_hint": "More hazards is bad, and less is better",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "Solar farm energy needs to be integrated into the grid using a substation",
            "axis_name": "Proximity to power substations (m)",
            "min": 1,
            "max": 1200000,
            "numerator": "power_substations_proximity_m",
            "denominator": "one",
            "evaluation_hint": "Closer location to a power station reduces infrastructure costs and improves efficiency. Lower proximity values mean smaller distance (closer=efficient), high proximity values = longer distance (inefficient). So lower values is better choice",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "Flat land is best for sun visibility",
            "axis_name": "Slope (°)",
            "min": 0,
            "max": 70,
            "numerator": "avg_slope_gebco_2022",
            "denominator": "one",
            "evaluation_hint": "Less slope means more flat surface, which is good",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "Solar farms need to be cool",
            "axis_name": "Days above 32°C (+1°C scenario) (days)",
            "min": 0,
            "max": 356,
            "numerator": "days_maxtemp_over_32c_1c",
            "denominator": "one",
            "evaluation_hint": "Fewer hot days are good",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "Solar farms should probably be closest to consumers",
            "axis_name": "Proximity to densely populated areas (m)",
            "min": 1,
            "max": 1200000,
            "numerator": "populated_areas_proximity_m",
            "denominator": "one",
            "evaluation_hint": "Closer location to populated areas reduces infrastructure costs and improves efficiency. Lower proximity values mean smaller distance (closer=efficient), high proximity values = longer distance (inefficient). So lower values is better choice",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "Solar substations need to be connected using powerlines",
            "axis_name": "Proximity to powerlines (m)",
            "min": 1,
            "max": 1200000,
            "numerator": "powerlines_proximity_m",
            "denominator": "one",
            "evaluation_hint": "Closer location to powerlines reduces infrastructure costs and improves efficiency. Lower proximity values mean smaller distance (closer=efficient), high proximity values = longer distance (inefficient). So lower values is better choice",
            "indicator_evaluation": "lower values are better"
        }
    ]
}'''

cropland_burn_risk_example = '''{
    "original_request": "Cropland burn risk",
    "analysis_name": "Cropland Wildfire Risk Assessment",
    "axes": [
        {
            "comment": "Drought increases the potential for cropland to burn. There's similar indicators: 'Drought hazard' (drought - index), 'Drought exposure' (drought_days_count).  Choosing `Drought exposure` to display more simple to interpret measure in days",
            "axis_name": "Number of days under drought impact, last year (n)",
            "min": 0,
            "max": 363,
            "numerator": "drought_days_count",
            "denominator": "one",
            "evaluation_hint": "More days of drought increase the risk of cropland burning.",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "High temperatures can enhance the risk of fires starting and spreading.",
            "axis_name": "Air temperature maximum (°C)",
            "min": -31,
            "max": 48.599998474121094,
            "numerator": "worldclim_max_temperature",
            "denominator": "one",
            "evaluation_hint": "Higher temperatures increase the risk of fires.",
            "indicator_evaluation": "lower values are better"
        },
        {
            "comment": "Cropland coverage directly relates to areas at risk of burning.",
            "axis_name": "Cropland landcover to Area (km²/km²)",
            "min": 2.5090622500482855e-8,
            "max": 1.0000000002450673,
            "numerator": "cropland",
            "denominator": "area_km2",
            "evaluation_hint": "More cropland area increases the potential risk of burns.",
            "indicator_evaluation": "higher values are better"
        }
    ]
}'''

