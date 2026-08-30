# docs/ 索引

小学生向け家庭学習アプリ **みんチャレ** の開発正本。  
`minsuke-springboot_02` と同様、**ループごとに人間承認** で進める。

## 読む順番

| 順番 | ファイル | 役割 |
| --- | --- | --- |
| 0 | [gate.md](./gate.md) | **いま止まっている場所**。最初に見る |
| 1 | [roles.md](./roles.md) | 人と AI の役割。AI は承認なしに実装しない |
| 2 | [loop.md](./loop.md) | ゲートA（提案）とゲートB（結果） |
| 3 | [spec.md](./spec.md) | **大まかな仕様（プロダクト正本の候補）** |
| 4 | [requirements.md](./requirements.md) | spec の箇条書き版 |
| 5 | [design.md](./design.md) | 詳細設計草案（API・テーブル）。仕様承認後 |
| 6 | [backlog.md](./backlog.md) | ループ単位のタスク |
| 7 | [dokkai.md](./dokkai.md) | おはなしの読解（L13） |
| 8 | [rika.md](./rika.md) | 理科ドリル（L14 草案） |
| 9 | [drill-prompt-rules.md](./drill-prompt-rules.md) | ドリル問題文の作成ルール |
| 10 | [misutes.md](./misutes.md) | 議事録・判断・ミス |
| 11 | [decisions.md](./decisions.md) | 採用/却下 |

## 原則

- コードより `docs/` が正本。
- 1ループが終わるたびに人間が GO するまで次へ進まない。
- 実装の事実は `misutes.md` に残す。
