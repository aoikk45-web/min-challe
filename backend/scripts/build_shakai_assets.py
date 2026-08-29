"""Generate prefecture map SVGs (MLIT white-map style). Map symbols: fetch_gsi_symbols.py."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_MAPS = ROOT / "frontend" / "public" / "shakai" / "maps"
DATA_DIR = ROOT / "backend" / "data" / "shakai"
GEOJSON_CACHE = DATA_DIR / "prefectures.geojson"

# 国土数値情報 行政区域データ（N03）に基づく都道府県境界 GeoJSON（47件）
GEOJSON_URL = "https://raw.githubusercontent.com/dataofjapan/land/master/japan.geojson"

PREF_KANJI: dict[str, str] = {
    "hokkaido": "北海道",
    "aomori": "青森県",
    "iwate": "岩手県",
    "miyagi": "宮城県",
    "akita": "秋田県",
    "yamagata": "山形県",
    "fukushima": "福島県",
    "ibaraki": "茨城県",
    "tochigi": "栃木県",
    "gunma": "群馬県",
    "saitama": "埼玉県",
    "chiba": "千葉県",
    "tokyo": "東京都",
    "kanagawa": "神奈川県",
    "niigata": "新潟県",
    "toyama": "富山県",
    "ishikawa": "石川県",
    "fukui": "福井県",
    "yamanashi": "山梨県",
    "nagano": "長野県",
    "gifu": "岐阜県",
    "shizuoka": "静岡県",
    "aichi": "愛知県",
    "mie": "三重県",
    "shiga": "滋賀県",
    "kyoto": "京都府",
    "osaka": "大阪府",
    "hyogo": "兵庫県",
    "nara": "奈良県",
    "wakayama": "和歌山県",
    "tottori": "鳥取県",
    "shimane": "島根県",
    "okayama": "岡山県",
    "hiroshima": "広島県",
    "yamaguchi": "山口県",
    "tokushima": "徳島県",
    "kagawa": "香川県",
    "ehime": "愛媛県",
    "kochi": "高知県",
    "fukuoka": "福岡県",
    "saga": "佐賀県",
    "nagasaki": "長崎県",
    "kumamoto": "熊本県",
    "oita": "大分県",
    "miyazaki": "宮崎県",
    "kagoshima": "鹿児島県",
    "okinawa": "沖縄県",
}

SVG_WIDTH = 420
SVG_HEIGHT = 520
PAD = 12


def load_geojson() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not GEOJSON_CACHE.exists():
        print(f"download: {GEOJSON_URL}")
        with urllib.request.urlopen(GEOJSON_URL, timeout=120) as resp:
            GEOJSON_CACHE.write_bytes(resp.read())
    return json.loads(GEOJSON_CACHE.read_text(encoding="utf-8"))


def iter_rings(geometry: dict):
    gtype = geometry["type"]
    if gtype == "Polygon":
        for ring in geometry["coordinates"]:
            yield ring
    elif gtype == "MultiPolygon":
        for polygon in geometry["coordinates"]:
            for ring in polygon:
                yield ring


def all_points(features: list[dict]) -> list[list[float]]:
    points: list[list[float]] = []
    for feature in features:
        for ring in iter_rings(feature["geometry"]):
            points.extend(ring)
    return points


def make_projector(points: list[list[float]]):
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    lon_span = max(max_lon - min_lon, 1e-9)
    lat_span = max(max_lat - min_lat, 1e-9)

    def project(lon: float, lat: float) -> tuple[float, float]:
        x = PAD + (lon - min_lon) / lon_span * (SVG_WIDTH - 2 * PAD)
        y = PAD + (max_lat - lat) / lat_span * (SVG_HEIGHT - 2 * PAD)
        return x, y

    return project


def ring_to_path(ring: list[list[float]], project) -> str:
    step = max(1, len(ring) // 140)
    sampled = ring[::step]
    if len(sampled) < 3:
        return ""
    x0, y0 = project(sampled[0][0], sampled[0][1])
    parts = [f"M {x0:.2f} {y0:.2f}"]
    for lon, lat in sampled[1:]:
        x, y = project(lon, lat)
        parts.append(f"L {x:.2f} {y:.2f}")
    parts.append("Z")
    return " ".join(parts)


def geometry_paths(geometry: dict, project) -> list[str]:
    paths: list[str] = []
    for ring in iter_rings(geometry):
        path = ring_to_path(ring, project)
        if path:
            paths.append(path)
    return paths


def map_svg(highlight_kanji: str, features_by_kanji: dict[str, dict], project) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" role="img">',
        f'  <rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" fill="#ffffff"/>',
    ]
    for kanji, feature in features_by_kanji.items():
        if kanji == highlight_kanji:
            continue
        for path in geometry_paths(feature["geometry"], project):
            lines.append(
                f'  <path d="{path}" fill="#ececec" stroke="#666666" stroke-width="0.7"/>'
            )
    highlight = features_by_kanji[highlight_kanji]
    for path in geometry_paths(highlight["geometry"], project):
        lines.append(
            f'  <path d="{path}" fill="#86efac" fill-opacity="0.9" '
            f'stroke="#15803d" stroke-width="1.4"/>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    geojson = load_geojson()
    features_by_kanji = {f["properties"]["nam_ja"]: f for f in geojson["features"]}
    missing = [kanji for kanji in PREF_KANJI.values() if kanji not in features_by_kanji]
    if missing:
        raise SystemExit(f"missing prefectures in geojson: {missing}")

    project = make_projector(all_points(geojson["features"]))
    OUT_MAPS.mkdir(parents=True, exist_ok=True)
    for code, kanji in PREF_KANJI.items():
        (OUT_MAPS / f"{code}.svg").write_text(
            map_svg(kanji, features_by_kanji, project),
            encoding="utf-8",
        )
    print(f"maps: {len(PREF_KANJI)}")


if __name__ == "__main__":
    main()
