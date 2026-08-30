# AGENTS.md

先に [docs/gate.md](docs/gate.md) を読む。状態が `waiting-A` / `waiting-B` / `stopped` なら **コードを書かない**。

続けて:

1. [docs/roles.md](docs/roles.md)
2. [docs/loop.md](docs/loop.md)
3. [docs/backlog.md](docs/backlog.md)

ドリル問題文・例文を書く・直すときは [docs/drill-prompt-rules.md](docs/drill-prompt-rules.md) も読む。

`おはなしのどくかい` の原稿・データ・ふりがな・採点は [docs/dokkai.md](docs/dokkai.md) を読む。

人間が今のゲートを承認したときだけ、その 1 ループを実装する。  
終わったら `docs/gate.md` を次の待ち状態にして停止する。
