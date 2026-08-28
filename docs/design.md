# design.md — MVP 設計

> 状態: **L1 進行中**。仕様は `spec.md` が正本。デモ子どもは 3年生。

## 技術構成

| 層 | 採用 | 理由 |
| --- | --- | --- |
| API | FastAPI / Python 3.12 | 指定スタック。MVP を速く閉じる |
| UI | React 18 + Vite + TypeScript | 指定スタック。HMR でループが速い |
| スタイル | Tailwind CSS + shadcn 風プリミティブ | 子ども向けにテーマを上書きしやすい |
| DB | SQLite + SQLAlchemy 2 | 追加サービス不要。家庭 1 件の MVP に十分 |
| 認証 | なし（デモ家庭 ID=1、ロール切替） | 1 週間 MVP。後から世帯ログインを載せる |

フロント開発サーバが `/api` をバックエンドへプロキシする。

- UI: `http://127.0.0.1:48221`
- API: `http://127.0.0.1:48222`

### L1 で実装するもの

- `GET /api/health`
- `GET /api/household?role=child|parent` → さくら家、みんすけ 3年生、おかあさん
- React シェル: ロール切替、下部ナビ（ホーム + 4本柱）
- 4本柱ページは仕様どおりの空状態。機能は L2 以降

## ディレクトリ

```
backend/          FastAPI
frontend/         Vite React
docs/             開発正本
```

## ドメインモデル

```
Household 1──* Member (parent | child)
Household 1──* PointRule
Household 1──* Reward
Member(child) 1──* StudyPlan
Member(child) 1──* DrillSession 1──* DrillQuestion
Member(child) 1──* PointLedger
Member(child) 1──* AlbumEntry
```

### 主要テーブル

- `households`: 家庭名
- `members`: 表示名, role(`parent`/`child`), grade(1-6, 子どものみ)
- `study_plans`: 日付, 科目, タイトル, 目安分, 完了日時
- `drill_sessions`: 種類, 学年, 状態, 正答数, 所要秒
- `drill_questions`: 式, 正解, 子ども入力, 正誤
- `point_rules`: event_key, ラベル, 点数, 有効フラグ
- `rewards`: 名前, 必要点数, 有効フラグ
- `point_ledger`: 増減, 理由, 関連 ID
- `album_entries`: kind, タイトル, 本文, スタンプ

### ポイント event_key（初期シード。保護者が改変可）

| key | 既定 |
| --- | --- |
| `drill_complete` | ドリル 1 回 10pt |
| `drill_perfect` | 全問正解 +5pt |
| `plan_complete` | 計画 1 件 8pt |
| `stamp` | できたねスタンプ 3pt（保護者が任意付与） |

カスタムルールは `custom_<uuid短縮>` を key にする。自動イベントには使わず、保護者の手動スタンプや将来拡張の受け皿。

ポイント計算はサーバ側のみ。ルールが無効または 0 点なら付与しない。交換は残高不足なら 400。

## API（プレフィックス `/api`）

ロールはクエリ `role=child|parent`。未指定は `child`。

| メソッド | パス | 用途 |
| --- | --- | --- |
| GET | `/household` | 家庭・メンバー・残高サマリ |
| GET | `/home` | 子どもホーム用まとめ |
| GET/POST | `/plans` | 計画一覧 / 作成 |
| PATCH/DELETE | `/plans/{id}` | 更新 / 削除 |
| POST | `/plans/{id}/complete` | 完了 + ポイント |
| POST | `/drills/start` | 10 問生成 |
| POST | `/drills/{id}/answer` | 1 問解答 |
| GET | `/drills/history` | 履歴 |
| GET/PUT | `/points/rules` | ルール取得 / 一括更新 |
| GET/POST | `/points/rewards` | ごほうび |
| PATCH | `/points/rewards/{id}` | ごほうび更新 |
| POST | `/points/rewards/{id}/redeem` | 交換 |
| POST | `/points/stamp` | できたねスタンプ |
| GET | `/points/ledger` | 履歴 |
| GET/POST | `/album` | アルバム |

## 画面

| パス | 主な利用者 | 内容 |
| --- | --- | --- |
| `/` | 子ども | 今日の計画、ポイント、ドリル開始 |
| `/drill` | 子ども | 出題〜結果 |
| `/plan` | 両方 | 週計画。保護者は編集 |
| `/points` | 両方 | 残高・履歴・ごほうび。保護者はルール編集 |
| `/album` | 両方 | タイムライン。保護者はメモ追加 |

グローバルヘッダーでロール切替。子どもナビは下部 4 アイコン。

## ドリル出題ルール

10 問、重複少なめの整数計算。わりざんは割り切れる問題のみ（MVP）。

| 学年 | たしざん/ひきざん | かけざん | わりざん |
| --- | --- | --- | --- |
| 1 | 1 桁（ひきざんは負にしない） | 使わない（2 の段までなら可） | なし→たしざんにフォールバック |
| 2 | 2 桁（100 未満） | 九九 | 九九の逆 |
| 3 | 3 桁 | 2桁×1桁 | 2桁÷1桁 |
| 4-6 | 3 桁、繰り上がり多め | 2桁×2桁 | 3桁÷1桁 |

## UI トーン

クリーム地、みかん色の主ボタン、空色のサブ、大きな丸角。コピーは子どもに敬語を使いすぎない。「できたね」「もういっかい」を標準にする。
