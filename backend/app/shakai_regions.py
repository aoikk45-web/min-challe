"""都道府県コード → 地域（地図表示・4択の範囲）。"""

from __future__ import annotations

REGIONS: dict[str, tuple[str, ...]] = {
    "hokkaido": ("hokkaido",),
    "tohoku": ("aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima"),
    "kanto": ("ibaraki", "tochigi", "gunma", "saitama", "chiba", "tokyo", "kanagawa"),
    "chubu": (
        "niigata",
        "toyama",
        "ishikawa",
        "fukui",
        "yamanashi",
        "nagano",
        "gifu",
        "shizuoka",
        "aichi",
        "mie",
    ),
    "kansai": ("shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama"),
    "chugoku": ("tottori", "shimane", "okayama", "hiroshima", "yamaguchi"),
    "shikoku": ("tokushima", "kagawa", "ehime", "kochi"),
    "kyushu": (
        "fukuoka",
        "saga",
        "nagasaki",
        "kumamoto",
        "oita",
        "miyazaki",
        "kagoshima",
        "okinawa",
    ),
}

PREF_CODE_TO_REGION: dict[str, str] = {
    code: region for region, codes in REGIONS.items() for code in codes
}

# 地域地図で描画するポリゴン重心の範囲（離島を除く）。min_lon, min_lat, max_lon, max_lat
REGION_DISPLAY_BBOX: dict[str, tuple[float, float, float, float]] = {
    "kanto": (138.5, 35.0, 141.0, 37.35),
}


def region_for_code(code: str) -> str:
    return PREF_CODE_TO_REGION[code]


def codes_in_same_region(code: str) -> tuple[str, ...]:
    region = PREF_CODE_TO_REGION.get(code)
    if region is None:
        raise KeyError(f"unknown prefecture code: {code}")
    return REGIONS[region]


def codes_for_kenkatachi(code: str) -> tuple[str, ...]:
    """地図表示・4択の範囲。沖縄は九州込み、九州は沖縄なし。"""
    region = region_for_code(code)
    codes = REGIONS[region]
    if region == "kyushu" and code != "okinawa":
        return tuple(item for item in codes if item != "okinawa")
    return codes
