import re

def extract_lat_lon_from_nml(nml_path):
    with open(nml_path, 'r') as file:
        content = file.read()

    lat_match = re.search(r'latitude\s*=\s*([\-\d.]+)', content)
    lon_match = re.search(r'longitude\s*=\s*([\-\d.]+)', content)

    if lat_match and lon_match:
        return float(lat_match.group(1)), float(lon_match.group(1))
    else:
        raise ValueError("Latitude or Longitude not found in the NML file.")
