# みんチャレ

小学生が楽しく自ら学ぶ家庭学習アプリ（FastAPI + React）。  
仕様の正本は [docs/spec.md](docs/spec.md)。開発はループごとに人間承認（[docs/loop.md](docs/loop.md)）。

デモ家庭: **さくら家** / 子ども **みんすけ（小学3年生）** / 保護者 **おかあさん**

## いま動くもの（L4 ブランチ）

- アプリ起動、家庭の表示、こども / おうちの人の切替
- 学習計画: 今週の一覧、保護者の追加・直す・消す、子どもの「できた」（完了でポイント）
- 計算ドリル: 10問の出題・その場採点・結果と履歴（完了でポイント）
- ポイント: 家庭ルール、スタンプ、残高、ごほうび交換
- アルバムの入口は空状態のまま

アルバム記録はあとのループです。

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
