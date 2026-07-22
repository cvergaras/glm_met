import argparse
import os
import sys

from .core import finalize, write_met_csv
from .parser import (
    extract_lat_lon_from_nml,
    extract_lw_type_from_nml,
    extract_start_stop_from_nml,
    extract_timezone_from_nml,
)
from .sources import get_source

SUBCOMMANDS = ('fetch', 'gee-logout')


def build_parser():
    parser = argparse.ArgumentParser(
        prog='glm-met',
        description="Build a GLM meteorological forcing file (met.csv) from "
                    "Open-Meteo (default, no account needed), SILO or Google Earth Engine")
    sub = parser.add_subparsers(dest='command')

    fetch = sub.add_parser('fetch', help='Fetch data and write met.csv (default command)')
    fetch.add_argument('nml_file', help='Path to glm3.nml file')
    fetch.add_argument('--source', choices=['openmeteo', 'silo', 'gee'], default=None,
                       help='Data source (default: openmeteo)')
    fetch.add_argument('--start', help='Start date (YYYY-MM-DD); default from nml')
    fetch.add_argument('--end', help='End date (YYYY-MM-DD); default from nml')
    fetch.add_argument('--output', default='met.csv', help='Output CSV file')
    fetch.add_argument('--rain-units', choices=['m/day', 'mm/day', 'mm/hour'],
                       default='m/day', help="Rain/Snow units (GLM default: m/day)")
    fetch.add_argument('--model', choices=['best_match', 'era5_land', 'era5'],
                       default='best_match', help='Open-Meteo reanalysis model')
    fetch.add_argument('--email',
                       help='Email address for SILO (or set GLM_MET_SILO_EMAIL)')
    fetch.add_argument('--project',
                       help='Google Cloud project ID (gee source; implies --source gee)')
    fetch.add_argument('--keep-cloud', action='store_true',
                       help='Also write a Cloud (fraction) column')

    sub.add_parser('gee-logout', help='Delete stored Earth Engine credentials')
    return parser


def run_fetch(args):
    source_name = args.source
    if source_name is None:
        if args.project:
            print("[INFO] --project given: using the gee source "
                  "(use --source to choose explicitly)")
            source_name = 'gee'
        else:
            source_name = 'openmeteo'

    email = args.email or os.environ.get('GLM_MET_SILO_EMAIL')
    if source_name == 'silo' and not email:
        raise SystemExit("[ERROR] SILO needs an email address: "
                         "pass --email or set GLM_MET_SILO_EMAIL")

    lat, lon = extract_lat_lon_from_nml(args.nml_file)
    tz_offset = extract_timezone_from_nml(args.nml_file)

    start, end = args.start, args.end
    if not start or not end:
        start_nml, stop_nml = extract_start_stop_from_nml(args.nml_file)
        start = start or start_nml.split()[0]
        end = end or stop_nml.split()[0]
    print(f"[INFO] Site: lat={lat}, lon={lon}, UTC{tz_offset:+d} | "
          f"{start} to {end} | source: {source_name}")

    lw_type = extract_lw_type_from_nml(args.nml_file)
    if lw_type and lw_type != 'LW_IN':
        print(f"[WARN] nml has lw_type = '{lw_type}' but this file provides "
              "incoming longwave (LongWave, W/m2). Set lw_type = 'LW_IN'.")

    source = get_source(source_name, model=args.model, email=email,
                        project=args.project)
    df = source.fetch(lat, lon, start, end, tz_offset)
    df = finalize(df, rain_units=args.rain_units, keep_cloud=args.keep_cloud)
    write_met_csv(df, args.output, timestep=source.timestep)
    print(f"[INFO] Saved {len(df)} rows to {args.output}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Back-compat: `glm-met glm3.nml ...` still works without the subcommand.
    if argv and argv[0] not in SUBCOMMANDS and argv[0] not in ('-h', '--help'):
        argv.insert(0, 'fetch')

    args = build_parser().parse_args(argv)
    if args.command == 'gee-logout':
        from .sources.gee import clear_ee_credentials
        clear_ee_credentials()
        print("[INFO] Earth Engine credentials removed")
    elif args.command == 'fetch':
        run_fetch(args)
    else:
        build_parser().print_help()


if __name__ == '__main__':
    main()
