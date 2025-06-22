import argparse
from .parser import extract_lat_lon_from_nml
from .climate import initialize_ee, fetch_era5_timeseries

def main():
    parser = argparse.ArgumentParser(description="Extract GEE climate data using GLM NML file")
    parser.add_argument("nml_file", help="Path to glm3.nml file")
    parser.add_argument("--start", default="1982-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="1982-01-02", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="met.csv", help="Output CSV file")
    args = parser.parse_args()

    lat, lon = extract_lat_lon_from_nml(args.nml_file)
    initialize_ee()
    df = fetch_era5_timeseries(lat, lon, args.start, args.end)

    columns = ['time', 'AirTemp', 'ShortWave', 'LongWave', 'RelHum', 'WindSpeed', 'Rain', 'Snow']
    df = df[columns]
    df.to_csv(args.output, index=False)
    print(f"Saved to {args.output}")

if __name__ == "__main__":
    main()
