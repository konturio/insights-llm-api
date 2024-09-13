''' ported from disaster-ninja-fe/src/utils/bivariate/labelFormatters.ts '''


def has_units(unit_id):
    return bool(unit_id and unit_id != 'other')


def format_bivariate_axis_unit(quotients):
    if not quotients:
        return None
    numerator, denominator = quotients

    # no numerator unit - don't show units
    if not has_units(numerator['unit']['id']):
        return None

    # numerator unit + denominator unit - one
    if denominator['name'] == 'one':
        return numerator['unit']['shortName']
    
    #  numerator unit + no denominator unit - show only numerator unit
    if not has_units(denominator['unit']['id']):
        return numerator['unit']['shortName']

    return f"{numerator['unit']['shortName']}/{denominator['unit']['shortName']}"


def format_bivariate_axis_label(quotients):
    if not quotients:
        return ''
    numerator, denominator = quotients

    # no numerator unit - don't show units
    if not has_units(numerator['unit']['id']):
        return f"{numerator['label']} to {denominator['label']}"

    # numerator unit + denominator unit - one
    if denominator['name'] == 'one':
        return f"{numerator['label']} ({numerator['unit']['shortName']})"
    
    #  numerator unit + no denominator unit - show only numerator unit
    if not has_units(denominator['unit']['id']):
        return f"{numerator['label']} to {denominator['label']} ({numerator['unit']['shortName']})"

    return f"{numerator['label']} to {denominator['label']} ({numerator['unit']['shortName']}/{denominator['unit']['shortName']})"


def set_axis_label(axis):
    quotients = axis.get('quotients', [])
    axis['label'] = format_bivariate_axis_label(quotients)
