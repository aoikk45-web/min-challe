# みんチャレ

小学生が、保護者に言われる前に自分から机に向かえる家庭学習アプリです。  
FastAPI + React。ログインなしで、**おおの家** のデータをそのまま蓄積できます。

- 子ども: **ゆうき**（小学3年生）
- 保護者: **おうちの人**（画面上の切り替え用）
- 画面上で「こども」と「おうちの人」を切り替えます

仕様の正本は [docs/spec.md](docs/spec.md)。開発はループごとに人間承認（[docs/loop.md](docs/loop.md)）。

## できること（4本柱）

下の4つの入口と、ホームから全部つながります。計画やドリルをやりきるとポイントが付き、アルバムに残ります。

| 柱 | 子ども | おうちの人 |
| --- | --- | --- |
| けいかく | 今日と今週を見て「できた」 | 追加・直す・消す |
| ドリル | たしざんなど 10問、かんじ・じゅくごのよみ | 履歴を見る |
| ポイント | 残高・交換 | ルール・ごほうび・ほめる（テスト100点など） |
| アルバム | できた記録 | 短い思い出メモ |

## 必要なもの

- Python **3.12**（3.14 では動きません）
- Node.js 22

Windows の `python` がストアの案内になるときは、`py -3.12` を使います。

## 起動

ブラウザは **フロント** を開きます。`http://127.0.0.1:48221`  
`/api` は API（`http://127.0.0.1:48222`）へプロキシされます。`--reload` は使わないでください（コードを変えたら API を再起動します）。

### Windows（PowerShell）

```powershell
# API
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 48222

# 別のターミナルで UI
cd frontend
npm install
npm run dev
```

### macOS / Linux

```bash
# API
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 48222

# 別のターミナルで UI
cd frontend
npm install
npm run dev
```

## テスト

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

macOS / Linux では venv を有効にしてから `pytest` でも同じです。
