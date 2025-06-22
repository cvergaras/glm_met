import argparse
from .parser import (
    extract_lat_lon_from_nml,
    extract_timezone_from_nml,
    extract_start_stop_from_nml
)
from .climate import initialize_ee, fetch_era5_timeseries

def main():
    parser = argparse.ArgumentParser(description="Extract GEE climate data using GLM NML file")
    parser.add_argument("nml_file", help="Path to glm3.nml file")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="met.csv", help="Output CSV file")
    args = parser.parse_args()

    lat, lon = extract_lat_lon_from_nml(args.nml_file)
    tz_offset = extract_timezone_from_nml(args.nml_file)

    # Use start/stop from NML file if not provided
    if not args.start or not args.end:
        start_nml, stop_nml = extract_start_stop_from_nml(args.nml_file)
        start = args.start or start_nml.split()[0]  # keep only date part
        end = args.end or stop_nml.split()[0]
        print(f"Fetching data from {start} to {end}")
    else:
        start, end = args.start, args.end
        

    initialize_ee()

    df = fetch_era5_timeseries(lat, lon, start, end, tz_offset)


    columns = ['time', 'AirTemp', 'ShortWave', 'LongWave', 'RelHum', 'WindSpeed', 'Rain', 'Snow']
    df = df[columns]
    df.to_csv(args.output, index=False)
    print(f"Saved to {args.output}")

if __name__ == "__main__":
    main()
