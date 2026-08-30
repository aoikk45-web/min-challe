from app.kokugo_kanji import annotate_furigana, kanji_grade, needs_furigana, unannotated_high_grade_kanji


def test_kanji_grade_lookup():
    assert kanji_grade("一") == 1
    assert kanji_grade("並") == 6
    assert kanji_grade("覚") is None


def test_annotate_adds_furigana_for_high_grade():
    text = annotate_furigana("片づけをしました。")
    assert "片(かた)づけ" in text
    assert unannotated_high_grade_kanji(text) == []


def test_annotate_compound_jukugo():
    assert annotate_furigana("洗濯物を") == "洗濯物(せんたくもの)を"
    assert annotate_furigana("準備をしました") == "準備(じゅんび)をしました"
    assert annotate_furigana("放課後に") == "放課後(ほうかご)に"
    assert annotate_furigana("絵本を読む") == "絵本(えほん)を読む"


def test_annotate_okurigana_rules():
    assert annotate_furigana("晴れた空") == "晴れた空"
    assert annotate_furigana("触れてみた") == "触(ふ)れてみた"
    assert annotate_furigana("頼りにする") == "頼(たよ)りにする"
    assert annotate_furigana("終わると") == "終(お)わると"
    assert annotate_furigana("積み重ねた") == "積(つ)み重ねた"
    assert annotate_furigana("忘れ物を探した") == "忘(わす)れ物(もの)を探(さが)した"
    assert annotate_furigana("取り出す") == "取(と)り出す"
    assert annotate_furigana("落ちた") == "落(お)ちた"


def test_annotate_skips_easy_kanji_and_katakana():
    assert annotate_furigana("今日は風が強い") == "今日は風が強い"
    assert annotate_furigana("ベランダに出た") == "ベランダに出た"
    assert "風(" not in annotate_furigana("風が気持ちよい")


def test_annotate_uses_contextual_readings():
    assert annotate_furigana("放課後に戻りました。") == "放課後(ほうかご)に戻(もど)りました。"
    assert annotate_furigana("床にはおもちゃが散らばっています。") == (
        "床(ゆか)にはおもちゃが散(ち)らばっています。"
    )
    assert annotate_furigana("自分の部屋") == "自分の部屋"


def test_annotate_preserves_mixed_kana():
    text = annotate_furigana("昆虫（こんちゅう）を観察しました。")
    assert unannotated_high_grade_kanji(text) == []


def test_neko_no_gogo_passage_furigana():
    """Golden reference: human-corrected s1_03 readings for grade-3 readers."""
    from scripts.dokkai_stories_catalog import all_stories

    passage = [s for s in all_stories() if s["id"] == "s1_03"][0]["passage"]
    expected = (
        "ゆうきの家には、白いねこがいます。名前はミルクです。今日は雨が降(ふ)っているので、外に出て遊ぶことができません。"
        "ゆうきは部屋のソファに座(すわ)って、ミルクを膝(ひざ)の上に乗(の)せました。"
        "ミルクはうれしそうにゴロゴロと喉(のど)を鳴らして、とても気持ちよさそうです。"
        "ゆうきは絵本(えほん)を読みながら、ゆっくりとページをめくりました。"
        "しばらくすると、ミルクは眠(ねむ)くなって、小さな足を気持ちよさそうに伸(の)ばしました。"
        "雨の音とねこの喉(のど)の音が、部屋の中に静(しず)かに広がっていきます。"
        "ゆうきは、ミルクと一緒(いっしょ)だと、退屈(たいくつ)な雨の日も平気だなと感(かん)じました。"
        "ゆうきは、そのあたたかい時間を忘(わす)れないように、心の中で何度(なんど)も思い返しました。"
    )
    assert annotate_furigana(passage) == expected
    for bad in ["座(ざ)", "乗(じょう)", "眠(みん)", "伸(しん)", "忘(ぼう)"]:
        assert bad not in annotate_furigana(passage)


def test_dokkai_story_fields_get_furigana():
    from app.dokkai import pick_story

    story = pick_story(1)
    for text in [story.title, story.passage, *[q.prompt for q in story.questions]]:
        assert unannotated_high_grade_kanji(text) == []
