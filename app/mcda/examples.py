solar_farms_example = '''{
    "request": "Best place to put solar farms",
    "axes": [
        {
            "comment": "Solar farms require sunlight",
            "axis_name": "Global Horizontal Irradiance (W/m²)",
            "min": 1,
            "max": 8,
            "numerator": {
                "name": "gsa_ghi",
                "label": "Global Horizontal Irradiance",
                "description": "Total amount of shortwave terrestrial irradiance received by a surface horizontal to the ground."
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "bad",
                "good"
            ]
        },
        {
            "comment": "Chopping down forest for solar farm is economically inseafible",
            "axis_name": "Forest landcover (km²/km²)",
            "min": 0,
            "max": 1,
            "numerator": {
                "name": "forest",
                "label": "Forest landcover",
                "description": "Area covered by forest - where tree canopy is more than 15%."
            },
            "denominator": {
                "label": "Area"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        },
        {
            "comment": "It is bad idea to put solar farm in disaster-prone area",
            "axis_name": "All disaster types exposure (days)",
            "min": 0,
            "max": 365,
            "numerator": {
                "name": "hazardous_days_count",
                "label": "All disaster types exposure",
                "description": "Number of days in the last year when severe and extreme disasters of any types were recorded."
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        },
        {
            "comment": "Solar farms energy needs to be integrated into the grid using a substation",
            "axis_name": "Proximity to power substations (m)",
            "min": 1,
            "max": 1200000,
            "numerator": {
                "name": "power_substations_proximity_m",
                "label": "Proximity to power substations",
                "description": "Distance to closest power substation"
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        },
        {
            "comment": "Flat land is best for sun visibility",
            "axis_name": "Slope (°)",
            "min": 0,
            "max": 70,
            "numerator": {
                "name": "avg_slope_gebco_2022",
                "label": "Slope",
                "description": "Average surface slope."
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        },
        {
            "comment": "Solar farms need to be cool",
            "axis_name": "Days above 32°C (+1°C scenario) (days)",
            "min": 0,
            "max": 356,
            "numerator": {
                "name": "days_maxtemp_over_32c_1c",
                "label": "Days above 32°C (+1°C scenario)",
                "description": "Number of days per year with a daily maximum temperature exceeding 32°C (90°F) at the \"recent\" climate warming scenario of +1.0°C. In 2017 the average surface temperature passed 1.0°C above the pre-industrial 1850-1900 average (a standard baseline time period in climate science)."
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        },
        {
            "comment": "Solar farms should probably be closest to consumers",
            "axis_name": "Proximity to densely populated areas (m)",
            "min": 1,
            "max": 1200000,
            "numerator": {
                "name": "populated_areas_proximity_m",
                "label": "Proximity to densely populated areas",
                "description": "Distance to closest Kontur Population cell with population > 80 ppl"
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        },
        {
            "comment": "Solar substations need to be connected using powerlines",
            "axis_name": "Proximity to powerlines (m)",
            "min": 1,
            "max": 1200000,
            "numerator": {
                "name": "powerlines_proximity_m",
                "label": "Proximity to powerlines",
                "description": "Distance to closest powerline"
            },
            "denominator": {
                "label": "1"
            },
            "sentiment": [
                "good",
                "bad"
            ]
        }
    ]
}'''
