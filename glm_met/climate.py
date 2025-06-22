import ee
import pandas as pd
import tqdm
from .utils import calculate_relative_humidity
from datetime import datetime, timezone, timedelta
import pytz
import math

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
        data = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=1000,
            maxPixels=1e6
        )
        date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd HH:mm').getInfo()
        props = data.getInfo()

        temp_k = props.get('temperature_2m', 273.15)
        dew_k = props.get('dewpoint_temperature_2m', 273.15)
        u = props.get('u_component_of_wind_10m', 0)
        v = props.get('v_component_of_wind_10m', 0)
        wind_speed = math.sqrt(u**2 + v**2)

        return {
            'time': date,
            'AirTemp': round(temp_k - 273.15, 2),
            'ShortWave_Jm2': props.get('surface_solar_radiation_downwards', 0),
            'LongWave_Jm2': props.get('surface_thermal_radiation_downwards', 0),
            'RelHum': round(calculate_relative_humidity(temp_k, dew_k), 2),
            'WindSpeed': round(wind_speed, 2),
            'Precipitation': round(props.get('total_precipitation_hourly', 0),4),
            'Snow': round(props.get('snowfall_hourly', 0),4),
        }

    images = collection.toList(collection.size())
    count = images.size().getInfo()
    results = []

    for i in tqdm.tqdm(range(count)):
        image = ee.Image(images.get(i))
        try:
            results.append(extract_data(image))
        except Exception as e:
            print(f"Failed at index {i}: {e}")

    df = pd.DataFrame(results)

    # Local time adjustment
    df['time'] = pd.to_datetime(df['time']) + timedelta(hours=tz_offset)
    df = df.sort_values('time').reset_index(drop=True)

    # Convert accumulated radiation to hourly flux (W/m²)
    # for var in ['ShortWave', 'LongWave']:
    #     df[var] = df[var] / timestep
    
    for var in ['ShortWave_Jm2', 'LongWave_Jm2']:
        col = var.replace('_Jm2', '')
        df[col] = df[var].diff() / timestep
        df[col] = df[col].clip(lower=0)

    df = df.drop(columns=['ShortWave_Jm2', 'LongWave_Jm2'])

    # # De-accumulate precipitation and snowfall and compute rain
    # df['Snow'] = df['Snow'].diff().clip(lower=0)
    # df['Precipitation'] = df['Precipitation'].diff().clip(lower=0)

    # Compute Rain as liquid precipitation
    df['Rain'] = (df['Precipitation'] - df['Snow'])#.clip(lower=0)  # from ERA5–land forum :contentReference[oaicite:4]{index=4}

    # Drop the original Precipitation column
    df = df.drop(columns=['Precipitation'])

    return df
