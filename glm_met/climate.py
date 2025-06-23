import ee
import pandas as pd
import math
from .utils import calculate_relative_humidity
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta

def initialize_ee():
    try:
        ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize()

def print_timestep_duration(collection):
    sorted_collection = collection.sort('system:time_start')
    img_list = sorted_collection.toList(2)

    img1 = ee.Image(img_list.get(0))
    img2 = ee.Image(img_list.get(1))

    t1 = img1.get('system:time_start').getInfo()
    t2 = img2.get('system:time_start').getInfo()

    if not isinstance(t1, int) or not isinstance(t2, int):
        print("[ERROR] Timestamps are invalid or missing.")
        return None

    dt1 = datetime.fromtimestamp(t1 / 1000, tz=timezone.utc)
    dt2 = datetime.fromtimestamp(t2 / 1000, tz=timezone.utc)
    timestep = (dt2 - dt1).total_seconds()
    print(f"[DEBUG] Time step between first two images: {timestep} seconds")
    return timestep

def fetch_era5_timeseries(lat, lon, start_date, end_date, tz_offset):
    point = ee.Geometry.Point([lon, lat])
    collection = (
        ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
        .filterBounds(point)
        .filterDate(start_date, end_date)
    )

    timestep = print_timestep_duration(collection)
   
    def extract_data(image):
        date = image.date().format('YYYY-MM-dd HH:mm')
        data = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=1000,
            maxPixels=1e6
        )
        # Combine region data with time as a dictionary using ee.Dictionary
        data_with_time = data.combine(ee.Dictionary({'time': date}))
        return ee.Feature(None, data_with_time)



    features = collection.map(extract_data).getInfo()['features']

    records = []
    for feat in features:
        props = feat['properties']
        temp_k = props.get('temperature_2m', 273.15)
        dew_k = props.get('dewpoint_temperature_2m', 273.15)
        u = props.get('u_component_of_wind_10m', 0)
        v = props.get('v_component_of_wind_10m', 0)
        wind_speed = math.sqrt(u**2 + v**2)
        records.append({
            'time': props['time'],
            'AirTemp': round(temp_k - 273.15, 2),
            'ShortWave_Jm2': props.get('surface_solar_radiation_downwards', 0),
            'LongWave_Jm2': props.get('surface_thermal_radiation_downwards', 0),
            'RelHum': round(calculate_relative_humidity(temp_k, dew_k), 2),
            'WindSpeed': round(wind_speed, 2),
            'Precipitation': round(props.get('total_precipitation_hourly', 0), 4),
            'Snow': round(props.get('snowfall_hourly', 0), 4),
        })

    df = pd.DataFrame(records)
    df['time'] = pd.to_datetime(df['time']) + timedelta(hours=tz_offset)
    df = df.sort_values('time').reset_index(drop=True)

    for var in ['ShortWave_Jm2', 'LongWave_Jm2']:
        col = var.replace('_Jm2', '')
        df[col] = df[var].diff() / timestep
        df[col] = df[col].clip(lower=0)

    df.drop(columns=['ShortWave_Jm2', 'LongWave_Jm2'], inplace=True)
    df['Rain'] = df['Precipitation'] - df['Snow']
    df.drop(columns=['Precipitation'], inplace=True)

    return df

def fetch_in_chunks(lat, lon, start_date, end_date, tz_offset, chunk='year'):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    results = []

    while start < end:
        next_end = min(start + (relativedelta(years=1) if chunk == 'year' else relativedelta(months=1)), end)
        print(f"[INFO] Fetching chunk: {start.date()} to {next_end.date()}")
        df_chunk = fetch_era5_timeseries(
            lat, lon,
            start.strftime('%Y-%m-%d'),
            next_end.strftime('%Y-%m-%d'),
            tz_offset
        )
        results.append(df_chunk)
        start = next_end

    return pd.concat(results, ignore_index=True)
