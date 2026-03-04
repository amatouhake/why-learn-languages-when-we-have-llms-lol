# セットアップガイド

## 前提条件

- Python 3.11+
- 語彙データ: `complete-hsk-vocabulary/` をプロジェクトルートにクローン
- 音声データ: `audio-cmn/` をプロジェクトルートにクローン

```bash
git clone https://github.com/drkameleon/complete-hsk-vocabulary.git
git clone https://github.com/hugolpz/audio-cmn.git
```

## インストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## データインポート

```bash
python import_data.py
```

実行のたびに `hsk.db` を再作成する（冪等）。回答データ（responses, streaks）は自動でバックアップ・復元される。出力例:

```
LLM data merged: 595/595 words updated
HSK 1: 150 words
HSK 2: 147 words
HSK 3: 298 words
Total: 595 words
With audio: 569
Progress restored: 42 responses, 2 streaks
```

`data/llm_generated.json` が存在すれば日本語訳と例文を自動マージ。なければスキップ（既存動作を壊さない）。

## 起動（ローカル開発）

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

ブラウザで `http://localhost:8000` を開く。

## Raspberry Pi へのデプロイ

### 初回セットアップ

Pi 上で直接、またはWSLから `ssh pi` で接続して:

```bash
cd ~/why-learn-languages-when-we-have-llms-lol
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python import_data.py
```

systemd サービス（`/etc/systemd/system/hsk.service`）— `<USER>` を自分のユーザー名に置き換え:

```ini
[Unit]
Description=HSK Trainer
After=network.target

[Service]
User=<USER>
WorkingDirectory=/home/<USER>/why-learn-languages-when-we-have-llms-lol
ExecStart=/home/<USER>/why-learn-languages-when-we-have-llms-lol/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now hsk.service
```

### 更新デプロイ

WSLから `deploy.sh` を使う:

```bash
# コード変更のみ（CSS/JS/Python修正など）
./deploy.sh

# データ更新あり（HSKレベル追加、llm_generated.json更新など）
# 回答データは保持される
./deploy.sh --reimport
```

`deploy.sh` は rsync でファイル同期 → (--reimport時) import_data.py 実行 → systemctl restart を行う。

### SSH 設定

WSLの `~/.ssh/config` — 値は `deploy.conf` を参照:

```
Host pi
  HostName <PI_HOST>
  User <PI_USER>
```
