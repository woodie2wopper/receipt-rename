#!/usr/bin/env python3
# -*- coding: utf-8 -*-

 

import os
import sys
import glob
import csv
from datetime import datetime
import base64
import pandas as pd
from pdf2image import convert_from_path
import google.generativeai as genai
import tempfile
import logging
import argparse
import shutil
from PIL import Image
import time
import re
import multiprocessing
import concurrent.futures

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='領収書の画像からテキストを抽出し、ファイル名を変更します。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  %(prog)s receipt.jpg
  %(prog)s -v receipt.jpg
  %(prog)s -d receipt.jpg
  %(prog)s --no-text receipt.pdf
  %(prog)s -y 2024 -- receipt.jpg
  %(prog)s --year 2024 2025 -- *.jpg
  %(prog)s receipt1.jpg receipt2.jpg receipt3.pdf
        '''
    )
    parser.add_argument('--', dest='ignored', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--debug', '-d', action='store_true', help='デバッグモードを有効にする')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細な出力を表示する')
    parser.add_argument('--no-text', action='store_true', help='テキストファイルを保存しない')
    parser.add_argument('--year', '-y', type=int, nargs='+', help='処理対象の年を指定（例：2024 2025）')
    parser.add_argument('file_paths', nargs='+', help='処理する領収書ファイルまたはディレクトリのパス（複数指定可）')
    return parser.parse_args()

def setup_logging(debug=False, verbose=False):
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    
    # カレントディレクトリにlogsフォルダを作成
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルのパスを設定
    log_file = os.path.join(log_dir, 'receipt_processing.log')
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def load_api_key():
    api_key_file = os.path.expanduser("~/.google_AI_API")
    try:
        with open(api_key_file, 'r') as f:
            for line in f:
                if line.startswith('GOOGLE_API_KEY='):
                    return line.split('=')[1].strip()
    except Exception as e:
        print(f"エラー: APIキーの読み込みに失敗しました: {e}")
        print(f"~/.google_AI_APIファイルを確認してください。")
        print("フォーマット: GOOGLE_API_KEY=あなたのAPIキー")
        sys.exit(1)
    return None

def generate_question(text, years=None):
    year_instruction = f"""
    提供するのは領収書の画像データです。OCRの結果から、会社名、支払日、支払い金額、摘要名を抽出するための質問です。
    以下の質問に対して、日本語で回答してください。

    ※重要な指示：
    1. 支払日が不明な場合は {years[0] if years else ''} 年として処理してください。
    2. 支払日の年が {years} のいずれでもない場合は、その旨を明確に示してください。
    3. 年が不明確な場合（例：月日のみ）は {years[0] if years else ''} 年として処理してください。
    4. 和暦の年号は以下のように西暦に変換してください：
       - 令和元年 = 2019年
       - 令和2年 = 2020年
       - 令和3年 = 2021年
       - 令和4年 = 2022年
       - 令和5年 = 2023年
       - 令和6年 = 2024年
       - 令和7年 = 2025年
       ※ "R06" "R6" "令6"なども令和6年として認識してください。
       ※ 登録番号などに含まれる"R06"も令和6年を表す可能性があります。
       ※ 和暦は令和しかありません。そのため、数字一桁なら令和の年号です。
    5. 日付の優先順位：
       1) 宿泊サービスの場合は宿泊最終日を支払日とする
       2) 支払済印の日付
       3) 領収印の日付
       4) 取引日/利用日
       5) 発行日
       6) 登録番号内の日付（例：T9810999176881 R07 01 15）
       ※ 支払期限や請求日は使用しないでください。
       ※ 将来の日付は支払日として使用しないでください。
       ※ 登録番号内の日付は「RXX XX XX」の形式で含まれることがあり、これは令和XX年XX月XX日を表します。
    6. 電気料金の特別ルール：
       1) 支払い先は「北陸電力」としてください
       2) 支払日は「OCRテキスト（TXTファイル）の内容を必ず参照し、利用月やご使用期間から"利用月の20日〜23日の最初の営業日"を推定してください」
       3) 例：2024年1月分の利用料金の場合、支払日は「2024-01-23」としてください
       4) ファイル名例：2024-01-23_14930円_北陸電力.jpg
    """ if years else ""

    return  f"""
    以下の領収書の内容から、会社名、支払日、支払い金額、摘要名を抽出してください。
    {year_instruction}
    支払い先の抽出ルール:
    1. 店舗名がある場合は、メインの店舗名のみを抽出（例：「ジュンク堂書店」）
    2. 支払い先と店舗名の両方がある場合は支払い先を優先（例：「楽天トラベル」）
    3. 括弧内の英語表記や店舗場所は除外
    4. チェーン店の場合は、チェーン名のみを使用（例：「ENEOS」）
    5. 電気料金の場合は「北陸電力」としてください

    {text}

    結果は以下のフォーマットで返してください（シンプルに）:
    会社名: [シンプルな会社名]
    支払日: [支払日（西暦で）]
    支払い金額: [支払い金額]
    摘要名: [摘要名]
    """

def pdf_to_jpeg(pdf_path, temp_dir, logger):
    """PDFの全ページをJPEGに変換"""
    try:
        images = convert_from_path(pdf_path)
        jpeg_paths = []
        for i, image in enumerate(images):
            jpeg_path = os.path.join(temp_dir, f"page_{i+1}.jpg")
            image.save(jpeg_path, 'JPEG')
            jpeg_paths.append(jpeg_path)
        return jpeg_paths
    except Exception as e:
        logger.error(f"PDFの変換に失敗しました: {e}")
        return None

def encode_image(image_path, logger):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"画像のエンコードに失敗しました: {e}")
        return None

def load_existing_text(text_file, logger):
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.debug(f"既存のテキストファイルの読み込みに失敗しました: {e}")
        return None

def create_backup_dir(original_dir, logger):
    """バックアップディレクトリを作成"""
    backup_dir = os.path.join(original_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        os.makedirs(backup_dir, exist_ok=True)
        logger.info(f"バックアップディレクトリを作成しました: {backup_dir}")
        return backup_dir
    except Exception as e:
        logger.error(f"バックアップディレクトリの作成に失敗しました: {e}")
        sys.exit(1)

def backup_file(file_path, backup_dir, logger):
    """ファイルをバックアップ"""
    try:
        backup_path = os.path.join(backup_dir, os.path.basename(file_path))
        shutil.move(file_path, backup_path)
        logger.debug(f"ファイルをバックアップフォルダに移動しました: {backup_path}")
        return True, backup_path
    except Exception as e:
        logger.error(f"ファイルのバックアップに失敗しました: {e}")
        return False, None

def is_tax_format(filename):
    """確定申告フォーマットかどうかをチェック"""
    pattern = r'\d{4}-\d{2}-\d{2}_\d+円_.+\.(jpg|jpeg|pdf|png)$'
    return bool(re.match(pattern, filename.lower()))

def process_file(file_path, args, logger, backup_dir):
    # 確定申告フォーマットのチェック
    if is_tax_format(os.path.basename(file_path)):
        print(f"スキップ: {os.path.basename(file_path)} (確定申告フォーマット)")
        return

    start_time = datetime.now()
    try:
        # 入力ファイルのディレクトリを取得
        input_dir = os.path.dirname(os.path.abspath(file_path))
        base, ext = os.path.splitext(file_path)
        temp_dir = None
        temp_files = []

        # 既存のテキストファイルをチェック
        text_file = f"{base}.txt"
        extracted_text = None
        if os.path.exists(text_file):
            logger.info(f"既存のテキストファイルを使用します: {text_file}")
            extracted_text = load_existing_text(text_file, logger)
        
        if not extracted_text:
            if ext.lower() == '.pdf':
                # 一時ディレクトリを作成
                temp_dir = tempfile.mkdtemp()
                temp_files = pdf_to_jpeg(file_path, temp_dir, logger)
                if not temp_files:
                    return
            else:
                temp_files = [file_path]

            # 全ページのテキストを結合
            all_text = []
            
            # Gemini APIで画像解析
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            for i, image_path in enumerate(temp_files, 1):
                # 画像をBase64エンコード
                base64_image = encode_image(image_path, logger)
                if not base64_image:
                    continue

                # テキスト抽出
                response = model.generate_content([
                    {
                        "mime_type": "image/jpeg",
                        "data": base64_image
                    },
                    """この領収書の内容を読み取ってください。
                    以下の形式で回答してください：

                    ※重要な指示：
                    和暦の年号は以下のように西暦に変換してください：
                    - 令和元年 = 2019年
                    - 令和2年 = 2020年
                    - 令和3年 = 2021年
                    - 令和4年 = 2022年
                    - 令和5年 = 2023年
                    - 令和6年 = 2024年
                    - 令和7年 = 2025年
                    ※ "R06" "R6" "令6"なども令和6年として認識してください。
                    ※ 登録番号などに含まれる"R06"も令和6年を表す可能性があります。
                    ※ 和暦は令和しかありません。そのため、数字一桁なら令和の年号です。

                    @入力ファイル名
                    """ + os.path.basename(file_path) + f"""
                    @ページ番号: {i}/{len(temp_files)}

                    ---OCRデータ---
                    [読み取ったテキストをそのまま出力してください]

                    ---支払い情報---
                    支払日：[支払日を記載（和暦は上記の通り西暦に変換）]
                    支払先：[支払先の正式名称]
                    支払金額：[支払金額を数字のみで記載]
                    摘要：[支払内容や品目名]

                    ---その他の情報---
                    [その他の重要な情報を箇条書きで記述]
                    """
                ])
                all_text.append(response.text)

            # 全ページのテキストを結合
            extracted_text = "\n\n=== ページの区切り ===\n\n".join(all_text)

            # Geminiの回答を一時的に保存
            if not args.no_text and extracted_text:
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                logger.info(f"Geminiの回答を保存しました: {text_file}")

        if args.verbose:
            logger.info("抽出されたテキスト:")
            logger.info(extracted_text)

        # 情報抽出
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(generate_question(extracted_text, args.year))
        result = response.text

        if args.debug:
            logger.debug("解析結果:")
            logger.debug(result)

        # 結果の解析
        rows = result.split('\n')
        table_data = [row.split(':') for row in rows if row.strip() and ':' in row]
        
        # データフレームに変換
        df = pd.DataFrame(table_data)
        
        if len(df) >= 4:
            # 会社名
            company_name = df[1][0].strip()
            # 支払日
            date_str = df[1][1].strip()
            # 日付のパース処理
            try:
                # 年月日の数字を抽出
                date_numbers = re.findall(r'(\d{4})(?:年)?[/-]?(\d{1,2})(?:月)?[/-]?(\d{1,2})(?:日)?', date_str)
                if date_numbers:
                    year, month, day = map(int, date_numbers[0])
                    date = datetime(year, month, day)
                else:
                    raise ValueError(f"日付の形式が認識できません: {date_str}")
            except ValueError as e:
                logger.error(f"日付エラー：{os.path.basename(file_path)}")
                logger.error(f"ファイル処理中にエラーが発生しました: {str(e)}")
                return None
            
            # 指定された年と異なる場合は処理を中止
            if args.year and date.year not in args.year:
                error_message = f"[年の不一致エラー] {os.path.basename(file_path)}: 指定された年（{args.year}）と異なります（{date.year}年）"
                print(error_message)
                logger.error(error_message)
                return

            date_formatted = date.strftime("%Y-%m-%d")
            # 支払い金額（数字のみ抽出）
            amount = ''.join(filter(str.isdigit, df[1][2].strip()))
            
            # 会社名のスペースをハイフンに置換
            company_name = company_name.replace(' ', '-')
            
            # 新しいファイル名のベース部分（拡張子なし）
            new_filename_base = f"{date_formatted}_{amount}円_{company_name}"
            
            # 画像/PDFファイルの新しいパス
            new_path = os.path.join(input_dir, f"{new_filename_base}{ext}")
            
            # ファイル名の重複チェックと連番付与
            counter = 1
            original_new_path = new_path
            while os.path.exists(new_path):
                # 既存のファイルと完全に同じ内容かチェック
                if os.path.exists(new_path) and os.path.getsize(file_path) == os.path.getsize(new_path):
                    with open(file_path, 'rb') as f1, open(new_path, 'rb') as f2:
                        if f1.read() == f2.read():
                            # 同一ファイルの場合は連番を付与
                            base_no_ext = os.path.splitext(original_new_path)[0]
                            new_path = f"{base_no_ext}_{counter}{ext}"
                            counter += 1
                            logger.info(f"同一ファイルを連番付きで保存します: {new_path}")
                            break
                
                # 異なるファイルの場合は連番を付与
                base_no_ext = os.path.splitext(original_new_path)[0]
                new_path = f"{base_no_ext}_{counter}{ext}"
                counter += 1

            # 元ファイルをバックアップディレクトリに移動
            backup_success, backup_path = backup_file(file_path, backup_dir, logger)
            if not backup_success:
                return

            # テキストファイルの処理
            if os.path.exists(text_file) and not args.no_text:
                # 新しい名前のテキストファイル
                new_text_file = os.path.join(input_dir, f"{new_filename_base}.txt")
                # テキストファイルを新しい名前で保存
                shutil.copy2(text_file, new_text_file)
                # 元のテキストファイルをバックアップ
                backup_file(text_file, backup_dir, logger)
                logger.info(f"テキストファイルを保存しました: {new_text_file}")
            
            # 処理済みファイルを元のディレクトリにコピー
            shutil.copy2(backup_path, new_path)
            logger.info(f"処理済みファイルを保存しました: {new_path}")
            
            # ログ出力
            log_file = os.path.join(input_dir, "receipt_log.csv")
            with open(log_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([new_path])

            # 処理時間の計算
            elapsed_time = datetime.now() - start_time
            elapsed_seconds = elapsed_time.total_seconds()

            # 処理結果の表示（常に表示）
            result_message = f"[処理時間 {elapsed_seconds:.2f}秒] 変更前：{os.path.basename(file_path)} -> 変更後：{os.path.basename(new_path)}"
            print(result_message)
            logger.info(result_message)

            # 詳細情報の表示（-vオプション時のみ）
            if args.verbose:
                print(f"  保存場所: {new_path}")
                if not args.no_text:
                    print(f"  テキストファイル: {new_text_file}")

    except Exception as e:
        # エラーメッセージを簡略化
        error_type = "日付エラー" if "time data" in str(e) else "処理エラー"
        error_message = f"[処理時間 {(datetime.now() - start_time).total_seconds():.2f}秒] {error_type}：{os.path.basename(file_path)}"
        print(error_message)
        logger.error(f"ファイル処理中にエラーが発生しました: {e}")
        logger.error(error_message)
        # エラー時はテキストファイルを入力ファイルと同じ名前で保存
        if not args.no_text and extracted_text and not os.path.exists(text_file):
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            logger.info(f"エラー時のテキストを保存しました: {text_file}")
    
    finally:
        # 一時ファイル・ディレクトリの削除
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"一時ディレクトリの削除に失敗しました: {e}")

def main():
    # コマンドライン引数を前処理
    args_list = sys.argv[1:]
    
    # --yearオプションの位置を探す
    year_options = ['--year', '-y']
    year_index = -1
    year_option = None
    
    for opt in year_options:
        if opt in args_list:
            year_index = args_list.index(opt)
            year_option = opt
            break
    
    if year_index != -1:
        try:
            # 引数を3つの部分に分割
            before_year = args_list[:year_index]  # --year より前の引数
            after_year = args_list[year_index + 1:]  # --year 以降の引数
            
            # 年の値を収集
            year_values = []
            file_args = []
            i = 0
            while i < len(after_year):
                if after_year[i].isdigit():
                    year_values.append(after_year[i])
                    i += 1
                elif after_year[i] == '--':
                    # -- 以降の引数は全てファイル名として扱う
                    file_args.extend(after_year[i + 1:])
                    break
                else:
                    # 数字でない引数はファイル名として扱う
                    file_args.append(after_year[i])
                    i += 1
            
            # 引数を再構築
            new_args = before_year
            if year_values:
                new_args.extend([year_option] + year_values)
            if file_args:
                new_args.extend(['--'] + file_args)  # -- を追加してファイル名を区切る
            
            sys.argv = [sys.argv[0]] + new_args
        except Exception as e:
            logger = setup_logging()
            logger.error(f"コマンドライン引数の解析に失敗しました: {e}")
            sys.exit(1)
    
    args = parse_arguments()
    logger = setup_logging(args.debug, args.verbose)

    # APIキーの設定
    GOOGLE_API_KEY = load_api_key()
    if not GOOGLE_API_KEY:
        logger.error("APIキーが設定されていません")
        sys.exit(1)

    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 処理対象ファイルのリストを作成
    target_files = []
    base_dir = None
    for file_path in args.file_paths:
        if os.path.isfile(file_path):
            if file_path.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                target_files.append(file_path)
                # 最初のファイルのディレクトリをベースディレクトリとして使用
                if base_dir is None:
                    base_dir = os.path.dirname(os.path.abspath(file_path))
            else:
                logger.warning(f"未対応のファイル形式です: {file_path}")
        elif os.path.isdir(file_path):
            # ディレクトリの場合は再帰的に対象ファイルを検索
            if base_dir is None:
                base_dir = os.path.abspath(file_path)
            for root, _, files in os.walk(file_path):
                for file in files:
                    if file.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                        target_files.append(os.path.join(root, file))
        else:
            logger.error(f"指定されたパスが存在しません: {file_path}")
    
    if not target_files:
        logger.error("処理対象のファイルが見つかりません")
        sys.exit(1)

    # 処理対象ファイルの総数を表示（確定申告フォーマットを除外）
    valid_files = [f for f in target_files if not is_tax_format(os.path.basename(f))]
    total_files = len(target_files)
    skipped_files = total_files - len(valid_files)
    
    print(f"処理対象ファイル数: {total_files}")
    if skipped_files > 0:
        print(f"スキップ対象: {skipped_files}件（確定申告フォーマット）")
    print(f"処理実行数: {len(valid_files)}件")

    # 共通のバックアップディレクトリを作成
    backup_dir = os.path.join(base_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        os.makedirs(backup_dir, exist_ok=True)
        logger.info(f"バックアップディレクトリを作成しました: {backup_dir}")
    except Exception as e:
        logger.error(f"バックアップディレクトリの作成に失敗しました: {e}")
        sys.exit(1)
    
    if len(valid_files) > 0:
        max_workers = min(multiprocessing.cpu_count(), len(valid_files))
        if max_workers > 1:
            print(f"並列処理を開始します（ワーカー数: {max_workers}）")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # バックアップディレクトリを引数として渡す
                futures = [executor.submit(process_file, file, args, logger, backup_dir) for file in valid_files]
                concurrent.futures.wait(futures)
        else:
            for file in valid_files:
                # バックアップディレクトリを引数として渡す
                process_file(file, args, logger, backup_dir)

    print("すべての処理が完了しました")

if __name__ == "__main__":
    main()        
