def calculate_relative_humidity(temp_k, dewpoint_k):
    temp_c = temp_k - 273.15
    dewpoint_c = dewpoint_k - 273.15

    es = 6.112 * 10**((7.5 * temp_c) / (temp_c + 237.3))
    e = 6.112 * 10**((7.5 * dewpoint_c) / (dewpoint_c + 237.3))

    rh = max(0, min((e / es) * 100, 100))
    return rh
