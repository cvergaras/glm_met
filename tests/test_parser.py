from glm_met.parser import (
    extract_lat_lon_from_nml,
    extract_lw_type_from_nml,
    extract_start_stop_from_nml,
    extract_timezone_from_nml,
)


def test_lat_lon(nml_path):
    lat, lon = extract_lat_lon_from_nml(nml_path)
    assert lat == 46.00881
    assert lon == -89.69953


def test_timezone(nml_path):
    assert extract_timezone_from_nml(nml_path) == -5


def test_start_stop(nml_path):
    start, stop = extract_start_stop_from_nml(nml_path)
    assert start.split()[0] == '1997-04-14'
    assert stop.split()[0] == '2007-06-17'


def test_lw_type(nml_path):
    lw = extract_lw_type_from_nml(nml_path)
    assert lw is None or isinstance(lw, str)
