import ee
import pandas as pd
import tqdm
from .utils import calculate_relative_humidity

def initialize_ee():
    try:
        ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize()

def fetch_era5_timeseries(lat, lon, start_date, end_date):
    point = ee.Geometry.Point([lon, lat])
    collection = (ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
                    .filterBounds(point)
                    .filterDate(start_date, end_date))

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

        return {
            'time': date,
            'AirTemp': round(temp_k - 273.15, 2) if temp_k else None,
            'ShortWave': round(props.get('surface_solar_radiation_downwards', 0) / 3600, 2),
            'LongWave': round(props.get('surface_thermal_radiation_downwards', 0) / 3600, 2),
            'RelHum': round(calculate_relative_humidity(temp_k, dew_k), 2),
            'WindSpeed': round(props.get('u_component_of_wind_10m', 0), 2),
            'Rain': round(props.get('total_precipitation', 0), 2),
            'Snow': round(props.get('snowfall', 0), 2)
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

    return pd.DataFrame(results)
