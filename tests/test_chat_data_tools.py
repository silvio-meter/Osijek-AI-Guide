"""Tests for get_events_today and get_wine_recommendations."""

from datetime import date

from chat_data_tools import (
    filter_events_today,
    filter_wine_recommendations,
    get_events_today,
    get_wine_recommendations,
    _load_events_catalog,
    _load_wine_catalog,
)


def test_filter_events_today_default_window():
    events = _load_events_catalog()
    result = filter_events_today(events, anchor=date(2026, 6, 16))
    assert len(result) >= 1
    assert all("title" in e for e in result)


def test_filter_wine_red_meat():
    wines = _load_wine_catalog()
    result = filter_wine_recommendations(wines, wine_type="crveno", food_pairing="meso")
    assert len(result) >= 1
    assert result[0]["type"] == "crveno"


def test_get_events_today_tool_json():
    out = get_events_today.invoke({"date": "", "category": ""})
    assert "events" in out
    assert "Koncert" in out or "events" in out


def test_get_wine_recommendations_tool_json():
    out = get_wine_recommendations.invoke(
        {"wine_type": "crveno", "price_range": "", "food_pairing": "meso"}
    )
    assert "recommendations" in out
    assert "Josić" in out or "crveno" in out