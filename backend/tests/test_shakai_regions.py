from app.shakai import PREFECTURES, _one_kenkatachi
from app.shakai_regions import codes_for_kenkatachi, codes_in_same_region


def test_prefecture_region_grouping():
    assert set(codes_in_same_region("akita")) == {
        "aomori",
        "iwate",
        "miyagi",
        "akita",
        "yamagata",
        "fukushima",
    }
    assert codes_in_same_region("okinawa") == codes_in_same_region("fukuoka")
    assert "okinawa" in codes_in_same_region("kagoshima")


def test_kyushu_kenkatachi_excludes_okinawa_unless_question_is_okinawa():
    kyushu_only = set(codes_for_kenkatachi("fukuoka"))
    assert "okinawa" not in kyushu_only
    assert len(kyushu_only) == 7
    with_okinawa = set(codes_for_kenkatachi("okinawa"))
    assert "okinawa" in with_okinawa
    assert len(with_okinawa) == 8


def test_kanto_map_excludes_distant_islands():
    from scripts.build_shakai_assets import (
        _polygon_centroid,
        display_feature,
        filter_geometry_for_region,
        iter_polygons,
        load_geojson,
    )

    geojson = load_geojson()
    tokyo = next(f for f in geojson["features"] if f["properties"]["nam_ja"] == "東京都")
    filtered = filter_geometry_for_region(tokyo["geometry"], "kanto")
    polygon_count = 1 if filtered["type"] == "Polygon" else len(filtered["coordinates"])
    assert polygon_count < len(tokyo["geometry"]["coordinates"])
    for polygon in iter_polygons(filtered):
        lon, lat = _polygon_centroid(polygon[0])
        assert lon <= 141.0
        assert lat >= 35.0
    assert display_feature(tokyo, "kanto")["geometry"] != tokyo["geometry"]


def test_kenkatachi_okinawa_choices_include_kyushu():
    from unittest.mock import patch

    okinawa = next(row for row in PREFECTURES if row["code"] == "okinawa")
    with patch("app.shakai.random.choice", lambda pool: okinawa):
        question = _one_kenkatachi(6, with_context=False)
    assert question.correct == "おきなわけん"
    assert question.choices is not None
    assert len(question.choices) == 4
    assert question.correct in question.choices
    assert sum(1 for choice in question.choices if choice == "おきなわけん") == 1
    assert sum(1 for choice in question.choices if choice != "おきなわけん") == 3


def test_kenkatachi_choices_are_regional():
    question = _one_kenkatachi(1, with_context=False)
    assert question.image_url
    code = question.image_url.rsplit("/", 1)[-1].removesuffix(".svg")
    region_names = {
        row["name"] for row in PREFECTURES if row["code"] in set(codes_for_kenkatachi(code))
    }
    assert question.correct in region_names
    assert set(question.choices or []) <= region_names
    assert len(question.choices) == 4
