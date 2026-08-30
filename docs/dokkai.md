# おはなしの読解（`おはなしのどくかい`）— L13 正本

小学3年生向け読解ドリルの **原稿・ふりがな・採点・データ運用** の参照先。  
問題文の文体ルールは [drill-prompt-rules.md](drill-prompt-rules.md) §4 と併用する。

## 原稿の出所

`backend/data/kokugo/dokkai_stories.json` に収録する **90話の本文・設問・選択肢・解説** は、  
[NotebookLM](https://notebooklm.google.com/) を用いて作成したあと、形式・採点・ふりがな検証のためリポジトリに取り込んだ。

- 人間が NotebookLM で下書き → JSON 化して `dokkai_stories.json` に配置
- アプリ側のふりがな・シャッフル・採点はコードが担当（原稿ファイル自体にルビは含めない）

## 概要

| 項目 | 内容 |
| --- | --- |
| 種別キー | `おはなしのどくかい` |
| 1セッション | ランダムに1話を出題 → **3問**（各4択＋解説） |
| バンク規模 | **90話**（ステージ1〜6、各15話） |
| 主人公 | **ゆうき**（小学3年生） |
| ステージアップ | 社会ドリル同型（5回全問正解で次ステージ） |

## 原稿の書き方

### 基本

- **ふりがなは原稿に書かない**（プレーンテキストのみ）。表示時に `kokugo_kanji.py` が自動付与する。
- 本文は **250〜350字** 程度（ステージ1-2はやや短く、5-6はやや長くてよい）。
- 設問は **3問固定**:
  1. `fact` — 本文から読み取れる事実
  2. `reason` — 理由・行動の意図（**本文に根拠があること**）
  3. `learning` — 学び・気持ちの変化
- 各問 **4択** ＋ 小学生向け `explanation`。
- `correct` は `choices` のいずれかと **完全一致**（コピペ推奨）。
- 正解が本文から自然に導けない設問は不可（推測だけの正解は×）。
- 選択肢の並びは原稿では **1番目に正解を置いてよい**（出題時にシャッフルされる）。

### ID・ステージ

- `id`: `s{ステージ}_{連番2桁}`（例: `s3_07`）
- `stage`: 1〜6（各ステージ15話）

### 正本例

- ステージ1 `s1_03`「ねことの午後」— ふりがなの期待出力は `tests/test_kokugo_kanji.py` の `test_neko_no_gogo_passage_furigana` を参照。

## 原稿データの形式（JSON）

正本ファイル: `backend/data/kokugo/dokkai_stories.json`

```json
[
  {
    "id": "s1_01",
    "stage": 1,
    "title": "あきらめないマラソン",
    "passage": "今日の体育は、マラソンでした。…",
    "questions": [
      {
        "type": "fact",
        "prompt": "ゆうきが走っているときに、声をかけてくれたのはだれですか。",
        "choices": ["となりのひろし君", "学校の先生", "お兄ちゃん", "おかあさん"],
        "correct": "となりのひろし君",
        "explanation": "となりのひろし君が、…と書かれています。"
      },
      {
        "type": "reason",
        "prompt": "…",
        "choices": ["…", "…", "…", "…"],
        "correct": "…",
        "explanation": "…"
      },
      {
        "type": "learning",
        "prompt": "…",
        "choices": ["…", "…", "…", "…"],
        "correct": "…",
        "explanation": "…"
      }
    ]
  }
]
```

## ふりがな（実行時ルール）

実装: `backend/app/kokugo_kanji.py` の `annotate_furigana()`

| パターン | 例 | 備考 |
| --- | --- | --- |
| 熟語（2字以上・中にかななし） | `準備(じゅんび)` `一緒(いっしょ)` `絵本(えほん)` | 漢字を切らない |
| 送り仮名つき動詞・形容詞 | `座(すわ)って` `乗(の)せました` `降(ふ)っている` | 訓読み。音読み禁止 |
| 小学1〜2年生の簡単な漢字 | `日` `手` `引` など | ルビなし |
| カタカナ語 | `ミルク` `ソファ` | ルビなし |
| 引っ張る系 | `引っ張(はっぱ)って` | `引` は1年生扱いでスキップし、`張` に `はっぱ` を付与 |

原稿は **ステップ1: ルビなしで自然な文を書く → ステップ2: 上記ルールで自動付与される想定** で書く。

## 出題・採点の挙動

| 処理 | タイミング | 実装 |
| --- | --- | --- |
| ふりがな付与 | セッション開始時 | `dokkai.py` → `drills.py` が DB に保存 |
| 選択肢シャッフル | 話を選んだとき | `dokkai.py` の `_shuffle_choices()` |
| 採点 | 回答送信時 | `normalize_reading(回答) == normalize_reading(正解)` |
| 正解キー | DB 保存時 | 選択肢と同じふりがな付き文字列（不一致で×になるのを防ぐ） |

**注意**: 進行中セッションは開始時の本文・選択肢が DB に残る。原稿やふりがなを直したあとは **新しいセッション** を始める（必要なら `backend/data/minchalle.db` を削除して API 再起動）。

## ビルド・検証コマンド

```powershell
cd backend

# 検証のみ（90話・正解整合・ふりがな付与可否）
.\.venv\Scripts\python.exe scripts\validate_dokkai_json.py data\kokugo\dokkai_stories.json

# dokkai.json を再生成（検証通過後にコピー）
.\.venv\Scripts\python.exe scripts\build_dokkai_bank.py
```

- 入力: `data/kokugo/dokkai_stories.json`
- 出力: `data/kokugo/dokkai.json`（API が読むバンク）

## 触るファイル

| ファイル | 役割 |
| --- | --- |
| `backend/data/kokugo/dokkai_stories.json` | 原稿正本（人間が編集） |
| `backend/data/kokugo/dokkai.json` | ビルド成果物 |
| `backend/scripts/validate_dokkai_json.py` | 原稿検証 |
| `backend/scripts/build_dokkai_bank.py` | バンク生成 |
| `backend/scripts/dokkai_stories_catalog.py` | JSON 読み込み（テスト等） |
| `backend/app/dokkai.py` | 話の選択・ふりがな・シャッフル |
| `backend/app/drills.py` | セッション・採点 API |
| `backend/app/kokugo_kanji.py` | ふりがなエンジン |
| `frontend/src/pages/DrillPage.tsx` | 読解 UI |
| `backend/tests/test_kokugo_kanji.py` | ふりがなゴールデンテスト |
| `backend/tests/test_drills.py` | セッション・シャッフルテスト |

## 原稿変更後のチェックリスト

1. `validate_dokkai_json.py` が通る
2. `build_dokkai_bank.py` で `dokkai.json` を再生成
3. `pytest`（特に `test_kokugo_kanji.py` / `test_drills.py`）
4. アプリで **新規セッション** を開始して表示・採点を確認
