# glm_met

A Python CLI tool to extract ERA5-Land hourly climate data from Google Earth Engine (GEE), using location coordinates read from a GLM `.nml` configuration file.

This tool is ideal for initializing meteorological forcing for lake models such as GLM-AED.

---

## 📦 Features

- Automatically reads `latitude` and `longitude` from a `glm3.nml` file
- Queries hourly ERA5-Land data for:
  - Air temperature
  - Shortwave & Longwave radiation
  - Relative humidity
  - Wind speed
  - Precipitation (rain & snow)
- Outputs a time series CSV (`met.csv`) in GLM-friendly format

---

## ✅ Installation

```bash
git clone <this-repo-url>
cd glm_met
pip install -e .
