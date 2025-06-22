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

def extract_timezone_from_nml(nml_path):
    with open(nml_path, 'r') as f:
        content = f.read()
    m = re.search(r'timezone\s*=\s*([+-]?\d+)', content)
    if m:
        return int(m.group(1))
    else:
        raise ValueError("Could not find 'timezone' in NML file.")
    
def extract_start_stop_from_nml(nml_path):
    with open(nml_path, 'r') as f:
        content = f.read()

    start_match = re.search(r"start\s*=\s*'([^']+)'", content)
    stop_match = re.search(r"stop\s*=\s*'([^']+)'", content)

    if start_match and stop_match:
        start_str = start_match.group(1).strip()
        stop_str = stop_match.group(1).strip()
        return start_str, stop_str
    else:
        raise ValueError("Could not find 'start' or 'stop' time in NML file.")