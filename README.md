# レシート管理ツール 概要

本リポジトリには、領収書・レシートの整理・リネーム・リストアップを自動化する2つのPythonプログラムが含まれています。

## プログラム一覧

### 1. receipt_rename.py
- 領収書画像・PDFからOCRで内容を抽出し、
- ファイル名を「日付_金額_支払い先」の形式に自動リネーム
- Gemini APIを利用した高精度な情報抽出
- 詳細仕様・使い方は [doc/receipt_rename.md](doc/receipt_rename.md) を参照

### 2. listup_receipts.py
- 指定ディレクトリ内のリネーム済みレシートファイルを一覧化
- ファイル名から日付・金額・支払先を抽出し、CSV形式で出力
- 年・月によるフィルタリングも可能
- 詳細仕様・使い方は [doc/receipt_rename.md](doc/receipt_rename.md) を参照

---

## インストール方法

1. 必要なパッケージのインストール:
```bash
pip install google-generativeai
pip install pdf2image
pip install pandas
```

2. Google AI APIキーの設定:
   - [Google AI Studio](https://makersuite.google.com/app/apikey)でAPIキーを取得
   - ホームディレクトリに`.google_AI_API`ファイルを作成
   - 以下の形式でAPIキーを記述:
     ```
     GOOGLE_API_KEY=あなたのAPIキー
     ```

---

詳細な仕様・使い方・注意事項は [doc/receipt_rename.md](doc/receipt_rename.md) をご覧ください。
