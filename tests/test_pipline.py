import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipeline import fixed_city_name, summarize_weather, transform_hourly_data


def test_fixed_city_name_removes_outer_spaces():
    result = fixed_city_name("   new york   ")

    assert result == "New York"


def test_fixed_city_name_removes_special_characters():
    result = fixed_city_name("@@london!!")

    assert result == "London"


def test_fixed_city_name_removes_extra_spaces():
    result = fixed_city_name("mexico     city")

    assert result == "Mexico City"


def test_fixed_city_name_corrects_capitalization():
    result = fixed_city_name("tOKyO")

    assert result == "Tokyo"


def test_transform_hourly_data():
    weather = {
        "hourly": {
            "time": [
                "2026-09-10T10:00",
                "2026-09-10T11:00"
            ],
            "temperature_2m": [
                25.0,
                27.5
            ],
            "precipitation": [
                0.0,
                0.2
            ]
        }
    }

    result = transform_hourly_data(weather, "New York")

    assert len(result) == 2
    assert pd.api.types.is_datetime64_any_dtype(result["time"])
    assert result["city"].tolist() == ["New York", "New York"]
    assert result["date"].iloc[0] == date(2026, 9, 10)


def test_transform_hourly_data_removes_missing_values():
    weather = {
        "hourly": {
            "time": [
                "2026-09-10T10:00",
                "2026-09-10T11:00"
            ],
            "temperature_2m": [
                25.0,
                None
            ],
            "precipitation": [
                0.0,
                0.2
            ]
        }
    }

    result = transform_hourly_data(weather, "New York")

    assert len(result) == 1
    assert result.isna().sum().sum() == 0


def test_summarize_weather():
    combined_df = pd.DataFrame({
        "city": [
            "New York",
            "New York",
            "New York"
        ],
        "date": [
            date(2026, 9, 10),
            date(2026, 9, 10),
            date(2026, 9, 10)
        ],
        "temperature_2m": [
            25.0,
            31.0,
            28.0
        ],
        "precipitation": [
            0.1,
            0.2,
            0.3
        ]
    })

    result = summarize_weather(combined_df)

    assert len(result) == 1
    assert result["max_temperature"].iloc[0] == 31.0
    assert result["total_precipitation"].iloc[0] == pytest.approx(0.6)