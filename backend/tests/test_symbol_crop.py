from scripts.fetch_gsi_symbols import _detect_label_crop_height


def test_detect_label_crop_finds_gap_above_label():
    h = 1000
    frac = [0.15] * 700 + [0.02] * 150 + [0.2] * 100 + [0.02] * 49 + [0.7]
    crop = _detect_label_crop_height(frac, h)
    assert crop > int(h * 0.60)
    assert crop < int(h * 0.85)


def test_detect_label_crop_fallback_when_no_gap():
    h = 1000
    frac = [0.15] * 1000
    crop = _detect_label_crop_height(frac, h)
    assert crop == int(h * 0.78)
