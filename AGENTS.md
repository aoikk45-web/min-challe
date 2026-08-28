# AGENTS.md

先に [docs/gate.md](docs/gate.md) を読む。状態が `waiting-A` / `waiting-B` / `stopped` なら **コードを書かない**。

続けて:

1. [docs/roles.md](docs/roles.md)
2. [docs/loop.md](docs/loop.md)
3. [docs/backlog.md](docs/backlog.md)

人間が今のゲートを承認したときだけ、その 1 ループを実装する。  
終わったら `docs/gate.md` を次の待ち状態にして停止する。
