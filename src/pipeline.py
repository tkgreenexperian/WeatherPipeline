import csv
import json
import os
import re
import time

import httpx
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

def transform_hourly_data(weather, clean_city):
    """Transform hourly API data into a cleaned DataFrame."""

    hourly_df = pd.DataFrame(weather["hourly"])

    hourly_df["time"] = pd.to_datetime(
        hourly_df["time"],
        errors="coerce"
    )

    hourly_df = hourly_df.dropna()

    hourly_df["city"] = clean_city
    hourly_df["date"] = hourly_df["time"].dt.date

    return hourly_df

def summarize_weather(combined_df):
    """Calculate daily maximum temperature and total precipitation."""

    daily_summary = combined_df.groupby(
        ["city", "date"],
        as_index=False
    ).agg({
        "temperature_2m": "max",
        "precipitation": "sum"
    })

    daily_summary = daily_summary.rename(columns={
        "temperature_2m": "max_temperature",
        "precipitation": "total_precipitation"
    })

    return daily_summary

def export_report(final_df):
    """Export the final weather report to a formatted Excel file."""

    os.makedirs("reports", exist_ok=True)

    report_path = "reports/weather_report.xlsx"

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        final_df.to_excel(writer, sheet_name="Daily Weather", index=False)

        worksheet = writer.sheets["Daily Weather"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for cell in worksheet[1]:
            cell.font = cell.font.copy(bold=True)

        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            worksheet.column_dimensions[column_letter].width = max_length + 2

    logger.info(f"Excel report exported to {report_path}")

def export_weather_alerts(final_df):
    """Export cities exceeding 30°C to a JSON alert file."""

    alerts = final_df[
        final_df["max_temperature"] > 30
    ][["city", "date", "max_temperature"]]

    alert_records = alerts.to_dict(
        orient="records"
    )

    alert_path = "reports/weather_alerts.json"

    with open(alert_path, "w") as file:
        json.dump(
            alert_records,
            file,
            indent=4
        )

    logger.info(
        f"JSON alert report exported to {alert_path}"
    )


start_time = time.time()

logger.info("Starting weather pipeline")
try:
    logger.info("Opening cities.csv")
    with open("data/cities.csv", "r", newline="") as file:
        reader = csv.DictReader(file)

        all_forecasts = []
        normalized_cities = []

        for row in reader:
            clean_city = fixed_city_name(row["city"])

            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

            normalized_cities.append({
                "city": clean_city,
                "latitude": latitude,
                "longitude": longitude
            })

            logger.info(f"Cleaned city: {clean_city}")

            weather = get_weather(latitude, longitude)

            missing_values = pd.DataFrame(weather["hourly"]).isna().sum().sum()

            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values for {clean_city}")

            hourly_df = transform_hourly_data(weather, clean_city)

            all_forecasts.append(hourly_df)

        cities_df = pd.DataFrame(normalized_cities)

        combined_df = pd.concat(all_forecasts, ignore_index=True)

        daily_summary = summarize_weather(combined_df)

        final_df = cities_df.merge(
            daily_summary,
            on="city",
            how="inner"
        )

        logger.info(f"Merged {len(final_df)} daily weather records")
        logger.info(f"Final DataFrame shape: {final_df.shape}")
        export_report(final_df)
        export_weather_alerts(final_df)
    end_time = time.time()
    logger.info(f"Created daily summary with {len(daily_summary)} records")
    logger.info("CSV processing completed successfully")
    logger.info(f"Total processing time: {end_time - start_time} seconds")

except FileNotFoundError:
    logger.error("cities.csv not found")

except Exception as e:
    logger.error(f"Unexpected error: {e}")