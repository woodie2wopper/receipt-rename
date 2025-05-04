#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class ReceiptExtractor:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            raise FileNotFoundError(f"指定されたディレクトリが見つかりません: {base_dir}")
        self.pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d+)円_(.*?)\.(jpg|jpeg|png|pdf)$', re.IGNORECASE)

    def extract_info(self, filename: str) -> Tuple[Dict[str, str], List[str]]:
        """ファイル名から情報を抽出し、不明な理由も返す"""
        # 全角ハイフンのチェック
        if '−' in filename:
            return {
                'date': '不明',
                'amount': '不明',
                'payee': '不明',
                'filename': filename
            }, ["全角ハイフン（−）が使用されています。半角ハイフン（-）を使用してください"]

        match = self.pattern.match(filename)
        if not match:
            return {
                'date': '不明',
                'amount': '不明',
                'payee': '不明',
                'filename': filename
            }, ["ファイル名の形式が異なります（YYYY-MM-DD_金額円_支払先.拡張子）"]

        date_str, amount, payee, _ = match.groups()
        reasons = []
        
        # 日付のチェック
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            # 存在しない日付のチェック
            if not (1 <= date.day <= 31 and 1 <= date.month <= 12):
                reasons.append(f"日付が不正です（{date_str}）")
                date_str = '不明'
        except ValueError:
            reasons.append(f"日付の形式が不正です（{date_str}）")
            date_str = '不明'

        # 金額のチェック
        if not amount.isdigit():
            reasons.append(f"金額が数値ではありません（{amount}）")
            amount = '不明'

        # 支払先のチェック
        if not payee.strip():
            reasons.append("支払先が空です")
            payee = '不明'

        return {
            'date': date_str,
            'amount': amount,
            'payee': payee,
            'filename': filename
        }, reasons

    def get_receipts_for_year(self, year: int) -> List[Tuple[Dict[str, str], List[str]]]:
        """指定年のレシート情報を取得"""
        receipts = []
        
        try:
            # 入力ディレクトリ内のファイルを直接検索
            for filename in os.listdir(self.base_dir):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')):
                    info, reasons = self.extract_info(filename)
                    receipts.append((info, reasons))
        except Exception as e:
            print(f"エラー: ファイルの読み込み中にエラーが発生しました: {e}", file=sys.stderr)
            return receipts

        return receipts

    def print_csv(self, receipts: List[Tuple[Dict[str, str], List[str]]], show_unknown: bool = False):
        """CSVを標準出力に出力"""
        try:
            # 不明なファイル名をフィルタリング
            filtered_receipts = [r[0] for r in receipts]
            if not show_unknown:
                filtered_receipts = [r[0] for r in receipts if r[0]['date'] != '不明' and r[0]['amount'] != '不明' and r[0]['payee'] != '不明']

            writer = csv.DictWriter(sys.stdout, fieldnames=['date', 'amount', 'payee', 'filename'])
            writer.writeheader()
            writer.writerows(filtered_receipts)

            # 不明なファイル名を表示
            if show_unknown:
                unknown_files = [(r[0], r[1]) for r in receipts if r[0]['date'] == '不明' or r[0]['amount'] == '不明' or r[0]['payee'] == '不明']
                if unknown_files:
                    print("\n=== 不明なファイル名 ===", file=sys.stderr)
                    for info, reasons in unknown_files:
                        print(f"{info['filename']} - 理由: {', '.join(reasons)}", file=sys.stderr)
                    print("=====================", file=sys.stderr)

        except Exception as e:
            print(f"エラー: CSVの出力中にエラーが発生しました: {e}", file=sys.stderr)
            raise

def main():
    import argparse

    parser = argparse.ArgumentParser(description='レシート情報をCSVに出力')
    parser.add_argument('--year', type=int, required=True, help='対象年')
    parser.add_argument('--input-dir', type=str, required=True, help='レシートファイルが直接格納されているディレクトリのパス')
    parser.add_argument('--show-unknown', action='store_true', help='不明なファイル名を表示')
    args = parser.parse_args()

    try:
        # 入力ディレクトリのパスを正規化
        input_dir = os.path.expanduser(args.input_dir)
        extractor = ReceiptExtractor(input_dir)
        
        print(f"{args.year}年のレシート情報を取得中...", file=sys.stderr)
        receipts = extractor.get_receipts_for_year(args.year)
        
        if not receipts:
            print(f"{args.year}年のレシートが見つかりませんでした。", file=sys.stderr)
            sys.exit(1)

        print(f"{len(receipts)}件のレシート情報を取得しました。", file=sys.stderr)
        extractor.print_csv(receipts, args.show_unknown)
        sys.exit(0)

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 