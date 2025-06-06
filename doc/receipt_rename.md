# receipt_rename.py / listup_receipts.py 詳細仕様・使い方

## receipt_rename.py

領収書のファイル名を統一された形式に整理し、OCRで内容を抽出するツールです。

### 機能
- 領収書の画像やPDFからOCRで情報を自動抽出
- ファイル名を「日付_金額_支払い先」の形式に統一
- 抽出したテキストの自動保存機能
- 元ファイルの自動バックアップ（バックアップフォルダに移動）
- 詳細なログ出力
- 和暦（令和）の自動変換機能
- 登録番号からの日付情報抽出機能

### 出力ファイル名の形式
`YYYY-MM-DD_金額円_支払い先.拡張子`
例：
- `2024-04-10_8657円_ENEOS-有明店.jpg`
- `2024-04-10_1200円_セブン-イレブン-赤坂店.pdf`

### 使用方法
```bash
# 基本的な使用方法（テキストファイルも自動保存）
./receipt_rename.py receipt.jpg

# デバッグモード（詳細なログを表示）
./receipt_rename.py -d receipt.jpg

# 詳細出力モード
./receipt_rename.py -v receipt.jpg

# テキスト保存を無効化
./receipt_rename.py --no-text receipt.jpg

# デバッグモードと詳細出力の併用
./receipt_rename.py -d -v receipt.jpg

# 複数ファイルの一括処理
./receipt_rename.py receipt1.jpg receipt2.jpg receipt3.pdf

# ワイルドカードによる一括処理
./receipt_rename.py *.jpg

# ディレクトリ内のすべてのファイルを処理
./receipt_rename.py 領収書フォルダ/
```

#### コマンドラインオプション
- `--debug`, `-d`: デバッグモードを有効化
- `--verbose`, `-v`: 詳細な出力を表示（処理時間を含む）
- `--no-text`: テキストファイルの保存を無効化（デフォルトでは保存する）

#### 複数ファイル処理
- 複数のファイルを直接指定可能
- ワイルドカード（`*.jpg`など）使用可能
- ディレクトリを指定した場合は再帰的に処理
- 自動的に並列処理を実行（CPU数に応じて最適化）
- 処理対象ファイル数を表示
- 未対応の拡張子は自動的にスキップ

### 出力情報
1. 基本出力（常に表示）:
   ```
   [処理時間 X.XX秒] 変更前：元のファイル名 -> 変更後：新しいファイル名
   ```
2. 詳細出力（-vオプション使用時）:
   ```
   [処理時間 X.XX秒] 変更前：元のファイル名 -> 変更後：新しいファイル名
     保存場所: /完全なパス/新しいファイル名
     テキストファイル: /完全なパス/新しいファイル名.txt
   ```
3. エラー時の出力:
   ```
   [処理時間 X.XX秒] エラー：処理に失敗したファイル名
   ```
4. ログ情報:
   - `receipt_processing.log`に記録
   - 処理の詳細
   - エラーメッセージ
   - 処理時間
   - ファイル操作の結果

### 日付の抽出ルール
1. 日付の優先順位：
   1. 支払済印の日付
   2. 領収印の日付
   3. 取引日/利用日
   4. 発行日
   5. 登録番号内の日付（例：T9810999176881 R07 01 15）
2. 登録番号の日付形式：
   - 形式：「RXX XX XX」（例：R07 01 15）
   - 意味：令和XX年XX月XX日
   - 例：R07 01 15 → 令和7年1月15日 → 2025年1月15日
3. 和暦の変換規則：
   - 令和元年 = 2019年
   - 令和2年 = 2020年
   - 令和3年 = 2021年
   - 令和4年 = 2022年
   - 令和5年 = 2023年
   - 令和6年 = 2024年
   - 令和7年 = 2025年
4. 和暦の表記ゆれ対応：
   - "R06" "R6" "令6" → 令和6年（2024年）
   - 数字一桁の場合は令和の年号として解釈
   - 登録番号内の年号も同様に解釈
5. 日付の制限：
   - 支払期限や請求日は使用しない
   - 将来の日付は使用しない
   - 指定された年と異なる場合は処理を中止
6. 電気料金の特別ルール：
   - 支払い先は「北陸電力」として処理
   - 支払日は利用月の20日〜23日の最初の営業日として推定
   - 例：2024年1月分の利用料金の場合、支払日は「2024-01-23」とする（1月23日が最初の営業日と仮定）
   - ファイル名例：2024-01-23_14930円_北陸電力.jpg

### 支払い先の抽出ルール
1. 店舗名がある場合は、メインの店舗名のみを抽出（例：「ジュンク堂書店」）
2. 支払い先と店舗名の両方がある場合は支払い先を優先（例：「楽天トラベル」）
3. 括弧内の英語表記や店舗場所は除外
4. チェーン店の場合は、チェーン名のみを使用（例：「ENEOS」）
5. 電気料金の場合は「北陸電力」として処理
6. 店舗名にスペースが含まれる場合はハイフン（-）で置換（例：「セブン イレブン」→「セブン-イレブン」）

### 出力ファイル
1. リネームされたファイル:
   - 処理済みファイルを新しい命名規則で保存
   - 形式: `YYYY-MM-DD_金額円_支払い先.拡張子`
   - スペースはハイフンに置換
   - 元のディレクトリに保存
2. テキストファイル（デフォルトで保存）:
   - OCRで抽出したテキストを保存
   - 処理成功時：
     - 新しいファイル名と同じ名前で`.txt`拡張子
     - 例：`2024-01-15_1840円_中日新聞.txt`
   - 処理失敗時：
     - 入力ファイル名と同じ名前で`.txt`拡張子
     - 例：`receipt.txt`（入力が`receipt.jpg`の場合）
   - `--no-text`オプションで保存を無効化可能
   - 元のディレクトリに保存
3. バックアップ:
   - 処理開始時に一つのバックアップディレクトリを作成
   - 全ての元ファイルと既存のテキストファイルを同じバックアップディレクトリに移動
   - バックアップディレクトリ名: `backup_YYYYMMDD_HHMMSS`
   - バックアップディレクトリは処理対象の最初のファイルまたはディレクトリと同じ場所に作成
   - 複数のディレクトリを処理する場合も、一つのバックアップディレクトリにまとめて保存
4. ログファイル:
   - `receipt_processing.log`にログを記録
   - 処理の詳細や発生したエラーを記録

### エラー処理
- ファイルが存在しない場合はエラーメッセージを表示
- APIキーが設定されていない場合はエラーメッセージを表示
- PDFの変換に失敗した場合はエラーログを記録
- 画像の処理に失敗した場合はスキップしてログを記録

### 依存パッケージ
- google-generativeai: Gemini APIを使用したOCR処理
- pdf2image: PDFから画像への変換
- pandas: データ処理
- base64: 画像エンコーディング
- logging: ログ管理

### パフォーマンス最適化
1. 並列処理:
   - 複数ファイルの同時処理
   - CPU数に応じて最適なワーカー数を自動設定
   - 処理対象ファイル数が2つ以上の場合に自動的に有効化
   - 進捗状況をリアルタイムで表示
2. 画像最適化:
   - PDFの解像度を200dpiに最適化
   - JPEG品質を85%に設定
   - 大きな画像は自動的にリサイズ（最大1600px）
3. キャッシュ機能:
   - 処理済みファイルの結果をキャッシュ
   - 同一ファイルの再処理を高速化
   - `.cache`ディレクトリに保存
4. API最適化:
   - 画像サイズの最適化
   - APIリクエストの制限制御
   - バッチ処理時の待機時間制御

### 処理時間の目安
- JPEG画像（標準サイズ）: 2-3秒
- PDF（1ページ）: 3-4秒
- 並列処理時: ファイル数÷CPU数×平均処理時間

### セキュリティとプライバシーに関する注意事項
#### APIキーの取り扱い
1. APIキーの設定:
   - [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
   - Googleアカウントでログイン
   - 「APIキーを作成」をクリック
   - 生成されたAPIキーをコピー
   - ホームディレクトリ（`~`）に`.google_AI_API`ファイルを作成
   - 以下の形式でAPIキーを記述:
     ```
     GOOGLE_API_KEY=あなたのAPIキー
     ```
   - ファイルのパーミッション: `600`（所有者のみ読み書き可能）に設定することを推奨
   ```bash
   chmod 600 ~/.google_AI_API
   ```
2. APIキーのセキュリティ:
   - APIキーは絶対にGitHubなどの公開リポジトリにコミットしないでください
   - `.google_AI_API`ファイルはバックアップ対象から除外することを推奨
   - 共有環境で使用する場合は、各ユーザーが独自のAPIキーを設定してください
   - APIキーは定期的にローテーションすることを推奨
   - 不要になったAPIキーは必ず無効化してください

#### ログファイルとバックアップの取り扱い
1. ログファイル（`receipt_processing.log`）:
   - 処理したファイル名、処理時間、エラー情報が記録されます
   - ログファイルには領収書の内容は記録されません
   - ログファイルは定期的に削除することを推奨
   - 機密情報を含むファイル名の場合は、ログ出力を無効化することを検討してください
2. バックアップディレクトリ:
   - 処理開始時に`backup_YYYYMMDD_HHMMSS`形式で作成
   - 元のファイルとテキストファイルが保存されます
   - バックアップは手動で削除する必要があります
   - 機密情報を含む領収書の場合は、バックアップの取り扱いに注意してください

#### 領収書情報の取り扱い
1. ログに記録される情報:
   - 処理したファイル名
   - 処理時間
   - エラー情報
   - 処理結果（成功/失敗）
2. 注意事項:
   - 領収書の内容自体はログに記録されません
   - ただし、ファイル名には日付、金額、支払い先が含まれます
   - 機密情報を含む領収書の場合は、ファイル名を変更してから処理することを推奨
   - 処理結果のテキストファイルには領収書の内容が含まれるため、適切に管理してください
3. プライバシー保護のための推奨事項:
   - 機密情報を含む領収書は別途管理することを推奨
   - 処理前にファイル名から機密情報を除去
   - 処理後のテキストファイルは適切に保管または削除
   - バックアップディレクトリは定期的に確認し、不要な場合は削除

---

## listup_receipts.py

### 概要
- 指定ディレクトリ内のリネーム済みレシートファイルを一覧化
- ファイル名から日付・金額・支払先を抽出し、CSV形式で出力
- 年・月によるフィルタリングも可能

### 使い方
```bash
./listup_receipts.py --input-dir <ディレクトリ>
# 年・月でフィルタ
./listup_receipts.py --input-dir <ディレクトリ> --year 2024 --month 1
# 不明なファイル名も表示
./listup_receipts.py --input-dir <ディレクトリ> --show-unknown
```

### 出力例
```
date,amount,payee,filename
2024-01-23,14930,北陸電力,2024-01-23_14930円_北陸電力.jpg
...
```

---

## ライセンス
このプロジェクトは[MITライセンス](../LICENSE)の下で公開されています。
