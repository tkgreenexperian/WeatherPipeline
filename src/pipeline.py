import csv
import re
import httpx
import time
import pandas as pd

from logger_config import logger

def fixed_city_name(city):
    """Clean and normalize city names."""

    # Remove leading and trailing spaces
    city = city.strip()

    # Remove special characters
    city = re.sub(r"[^a-zA-Z\s]", "", city)

    # Remove extra spaces between words
    city = " ".join(city.split())

    # Convert to proper title case
    city = city.title()

    return city

def get_weather(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
    "latitude": latitude,
    "longitude": longitude,
    "hourly": "temperature_2m,precipitation",
    "timezone": "auto"
    }

    response = httpx.get(url,params=params,verify=False)

    response.raise_for_status()

    return response.json()

start_time = time.time()

logger.info("Starting weather pipeline")
try:
    logger.info("Opening cities.csv")
    with open("data/cities.csv", "r", newline="") as file:
        reader = csv.DictReader(file)
        all_forecasts = []
        for row in reader:
            clean_city = fixed_city_name(row["city"])

            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

            logger.info(f"Cleaned city: {clean_city}")

            weather = get_weather(latitude, longitude)

            hourly_df = pd.DataFrame(weather["hourly"])

            hourly_df["time"] = pd.to_datetime(hourly_df["time"], errors="coerce")

            missing_values = hourly_df.isna().sum().sum()

            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values for {clean_city}")
                hourly_df = hourly_df.dropna()

            hourly_df["city"] = clean_city
            hourly_df["date"] = hourly_df["time"].dt.date
            all_forecasts.append(hourly_df)

            logger.info(f"Loaded {len(hourly_df)} valid hourly records for {clean_city}")
            logger.info(f"Finished processing weather data for {clean_city}")

    combined_df = pd.concat(
        all_forecasts,
        ignore_index=True
    )

    daily_summary = combined_df.groupby(
        ["city", "date"],
        as_index=False
    ).agg({
        "temperature_2m": "max",
        "precipitation": "sum"
    })
    daily_summary = daily_summary.rename(
    columns={
        "temperature_2m": "max_temperature",
        "precipitation": "total_precipitation"
    }
)
    print(daily_summary.head())
    end_time = time.time()
    logger.info(f"Created daily summary with {len(daily_summary)} records")
    logger.info("CSV processing completed successfully")
    logger.info(f"Total processing time: {end_time - start_time} seconds")

except FileNotFoundError:
    logger.error("cities.csv not found")

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    print(f"ERROR: {e}")