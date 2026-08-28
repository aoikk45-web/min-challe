# みんチャレ

小学生が楽しく自ら学ぶ家庭学習アプリ（FastAPI + React）。  
仕様の正本は [docs/spec.md](docs/spec.md)。開発はループごとに人間承認（[docs/loop.md](docs/loop.md)）。

デモ家庭: **さくら家** / 子ども **みんすけ（小学3年生）** / 保護者 **おかあさん**

## いま動くもの（L1）

- アプリ起動、家庭の表示、こども / おうちの人の切替
- 4本柱（計画・ドリル・ポイント・アルバム）の入口と空状態

学習計画の保存、ドリル、ポイント計算、アルバム記録は次のループです。

## 起動

必要: Python 3.12、Node.js 22

```bash
# API  http://127.0.0.1:48222
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 48222

# UI  http://127.0.0.1:48221
cd frontend
npm install
npm run dev
```

ブラウザはフロントのポートを開く（`/api` は API へプロキシされます）。

## テスト

```bash
cd backend
source .venv/bin/activate
pytest
```
