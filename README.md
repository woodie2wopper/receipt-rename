# レシート管理ツール 概要

本リポジトリには、領収書・レシートの整理・リネーム・リストアップを自動化する2つのPythonプログラムが含まれています。

## プログラム一覧

### 1. receipt_rename.py
- 領収書画像・PDFからOCRで内容を抽出し、
- ファイル名を「日付_金額_支払い先」の形式に自動リネーム
- LLM（`gemini` または `local-llm(Open WebUI)`）を利用した情報抽出
- 詳細仕様・使い方は [doc/receipt_rename.md](doc/receipt_rename.md) を参照

### 2. listup_receipts.py
- 指定ディレクトリ内のリネーム済みレシートファイルを一覧化
- ファイル名から日付・金額・支払先を抽出し、CSV形式で出力
- 年・月によるフィルタリングも可能
- 詳細仕様・使い方は [doc/listup_receipts.md](doc/listup_receipts.md) を参照

---

## セットアップと実行

1. 初回セットアップ（venv作成と依存インストール、Python 3.11使用）:
```bash
./scripts/ensure_venv.sh
```

2. 仮想環境の有効化:
```bash
source .venv/bin/activate
```

3. LLM設定（`gemini` / `local-llm`）:
   - 本リポジトリは公開リポジトリです。APIキーやトークンは**絶対にコミットしない**でください。
   - 秘密情報は `~/.SecretVault` などのホーム配下（リポジトリ外）で管理してください。
   - **gemini（デフォルト）**:
     - [Google AI Studio](https://makersuite.google.com/app/apikey)でAPIキーを取得
     - `~/.SecretVault/GEMINI_API.txt` に以下を保存
       ```
       GOOGLE_API_KEY=your_google_api_key
       ```
   - **local-llm（Open WebUI, 環境依存の一例）**:
     - `~/.SecretVault/GX10_OLLAMA_API.txt` に以下を保存
       ```
       export LLM_BASE_URL="http://192.168.1.40:12000"
       export OPENWEBUI_TOKEN="your_openwebui_token"
       export LLM_MODEL="qwen2.5:7b"
       ```
     - 実行前に読み込む
       ```bash
       source ~/.SecretVault/GX10_OLLAMA_API.txt
       export LLM_PROVIDER=openwebui
       ```

4. 実行方法（ラッパー経由）:
```bash
bin/receipt_rename <path_or_dir>
# または
bin/listup_receipts --input-dir <dir> [--year 2025 --month 1]
```

備考:
- `pdf2image`の外部依存（poppler）は本仕様では扱いません。

---

詳細な仕様・使い方・注意事項は [doc/receipt_rename.md](doc/receipt_rename.md) をご覧ください。
