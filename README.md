# glm_met

Build a meteorological forcing file (`met.csv`) for the [General Lake Model (GLM)](https://github.com/AquaticEcoDynamics/GLM) from a `glm3.nml` file — with **no account, no API key and no setup** in the default configuration.

The tool reads `latitude`, `longitude`, `timezone`, `start` and `stop` from your GLM `.nml` file, downloads hourly meteorological data, converts everything to GLM conventions and writes a ready-to-use `met.csv`.

## Quickstart

```bash
pip install .
glm-met glm3.nml
```

That's it — this uses the Open-Meteo archive (ERA5 family reanalysis) and needs no registration.

## Data sources

| Source | Coverage | Timestep | Auth required | Notes |
|---|---|---|---|---|
| `openmeteo` (default) | Global, 1940–present | hourly | none | ERA5 / ERA5-Land via the free [Open-Meteo archive API](https://open-meteo.com/en/docs/historical-weather-api) |
| `silo` | Australia, 1889–present | hourly | email address only | **SILO-corrected hourly**: Open-Meteo hourly base, adjusted per day so temperature, rain and solar match [SILO](https://www.longpaddock.qld.gov.au/silo/)'s station-interpolated daily grids |
| `gee` | Global, 1950–present | hourly | Google Cloud project registered with Earth Engine | Original ERA5-Land path; kept for users who already have credentials (`pip install .[gee]`) |

```bash
# default (Open-Meteo, ERA5 family)
glm-met glm3.nml

# pin the reanalysis model
glm-met glm3.nml --model era5_land

# Australia, corrected against SILO daily grids
glm-met glm3.nml --source silo --email you@example.com   # or set GLM_MET_SILO_EMAIL

# legacy Google Earth Engine path
pip install .[gee]
glm-met glm3.nml --project YOUR_GCP_PROJECT              # implies --source gee
glm-met gee-logout                                       # remove stored EE credentials
```

Common options: `--start/--end YYYY-MM-DD` (default: from the nml `&time` block), `--output met.csv`, `--rain-units {m/day,mm/day,mm/hour}`, `--keep-cloud` (adds a `Cloud` fraction column).

## Output format

```
time,AirTemp,ShortWave,LongWave,RelHum,WindSpeed,Rain,Snow,SoilTemp
2000-06-01 00:00,13.1,0.0,380.71,57.0,3.57,0.0168,0.0,13.9
2000-06-01 01:00,11.8,0.0,373.84,73.0,3.51,0.0312,0.0,13.1
```

| Column | Unit | GLM setting |
|---|---|---|
| AirTemp | °C | |
| ShortWave | W/m² | `met_sw = .true.` |
| LongWave | W/m² (incoming) | `lw_type = 'LW_IN'` |
| RelHum | % | |
| WindSpeed | m/s | |
| Rain | **m/day** (GLM's default rain intensity, even in hourly files) | `rain_factor = 1.0` |
| Snow | m/day water-equivalent | `snow_sw = .true.` if used |
| SoilTemp | °C (~0–7 cm depth) | extra column; ignored by GLM |

Times are local standard time (the nml `timezone` offset applied to UTC data).

### Longwave radiation

Open-Meteo and SILO do not provide incoming longwave radiation, so `LongWave` is **estimated** from air temperature, humidity and cloud cover: Brutsaert (1975) clear-sky emissivity with the Crawford & Duchon (1999) cloud correction. Compared against ERA5's radiative-transfer longwave this estimate is typically within a few tens of W/m² but smoother hour-to-hour. If your application is sensitive to longwave, use `--source gee` (ERA5-Land's own `surface_thermal_radiation_downwards`) or supply measured values.

### SILO-corrected hourly (`--source silo`)

For Australian sites, SILO's daily grids (interpolated from Bureau of Meteorology stations) are usually closer to ground truth than raw reanalysis, but they are daily and lack wind and longwave. This source keeps the hourly *shape* from Open-Meteo and forces the daily *aggregates* to match SILO:

- **AirTemp**: shifted per day so the daily mean equals SILO's `(max_temp + min_temp)/2`
- **Rain**: scaled per day so the daily total equals SILO's `daily_rain` (SILO rain on a reanalysis-dry day is spread uniformly; SILO-dry days are zeroed)
- **ShortWave**: scaled per day so the daily mean equals SILO's `radiation`
- **RelHum**: recomputed from SILO's vapour pressure against the adjusted temperature
- **WindSpeed / Snow / SoilTemp**: Open-Meteo passthrough; **LongWave** re-derived from the adjusted values

Each run reports the nearest BoM stations feeding SILO's interpolation at your site (with distances) and an adjustment summary (days matched, temperature offset, rain totals, shortwave factors), so you can see exactly what SILO changed. Add `--plot [file.png]` for a daily-aggregate comparison figure of raw ERA5 vs SILO vs the adjusted output (`pip install .[plots]` for matplotlib).

## Python API

```python
from glm_met import fetch_met

df = fetch_met(lat=-27.5, lon=151.9, start='2020-01-01', end='2020-12-31',
               tz_offset=10, source='silo', email='you@example.com')
df.to_csv('met.csv', index=False)
```

## Development

```bash
pip install -e .[dev]
pytest
```

Tests run offline against recorded API responses in `tests/fixtures/`.

## Roadmap

- Validation of any source against local measurements (stats, plots, optional bias correction)
- SILO PatchedPoint (station) mode
- Cloud-cover output for GLM's `lw_type = 'LW_CC'`
- NASA POWER source

## Contact

Developed by Claudio Vergara-Saez.
Feel free to submit issues or suggestions.
