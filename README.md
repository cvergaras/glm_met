# glm_met

A Python CLI tool to extract ERA5-Land hourly climate data from Google Earth Engine (GEE), using location coordinates read from a GLM `.nml` configuration file.

This tool is ideal for initializing meteorological forcing for lake models such as GLM-AED.

## Features

- Automatically reads `latitude` and `longitude` from a `glm3.nml` file
- Queries hourly ERA5-Land data for:
  - Air temperature  
  - Shortwave & Longwave radiation  
  - Relative humidity  
  - Wind speed  
  - Precipitation (rain & snow)
- Outputs a time series CSV (`met.csv`) in GLM-friendly format

## Installation

```bash
git clone <this-repo-url>
cd glm_met
pip install -e .
```

This installs the CLI tool `glm-met`.

## Usage

### 1. Authenticate with Google Earth Engine (first time only)

Before your first use, you must authenticate with your Google Earth Engine account:

```bash
python -c "import ee; ee.Authenticate(auth_mode='paste')"
```

This will print a URL in your terminal. Open it in your browser, sign in with your Google account, and paste the generated token back into the terminal.

Once authenticated, credentials will be stored and reused automatically — you only need to do this once per machine.

### 2. Run the tool

```bash
glm-met glm3.nml --start 2015-07-15 --end 2015-07-16 --output met.csv
```

- `glm3.nml`: Path to your GLM configuration file  
- `--start` and `--end`: Date range in `YYYY-MM-DD` format  
- `--output`: Path to output CSV file (default: `met.csv`)

## Output Format

The CSV output will look like this:

```
time,AirTemp,ShortWave,LongWave,RelHum,WindSpeed,Rain,Snow
2015-07-15 00:00,24.79,1.75,402.41,79.75,1.73,0,0
2015-07-15 01:00,20.92,0.00,398.39,81.88,1.71,0,0
...
```

Units:
- AirTemp: °C  
- ShortWave / LongWave: W/m²  
- RelHum: %  
- WindSpeed: m/s  
- Rain / Snow: mm

## Requirements

- Python ≥ 3.7  
- Internet access  
- Earth Engine account: [https://signup.earthengine.google.com](https://signup.earthengine.google.com)

## Development

This package uses:

- `earthengine-api`  
- `pandas`  
- `tqdm`

## Example `glm3.nml` File

```fortran
&morphometry
   lake_name = 'Sparkling Lake'
   latitude = 46.00881
   longitude = -89.69953
   crest_elev = 190.0
/
```

## Contact

Developed by Claudio Vergara-Saez 
Feel free to submit issues or suggestions.
