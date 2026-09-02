# Security.py
import os
import re
import json
from pathlib import Path

class SensitiveDataMasker:
    def __init__(self):
        # الگوی پسورد
        self.pass_pattern = re.compile(r"\{\{SECRET_PASS:(.*?)\}\}")
        
        # الگوی جامع IPv4: شامل فاصله‌ها بین اعداد و نقطه‌ها، و پورت اختیاری
        # مثال‌ها: 10.212.10.212 یا 10 . 212 . 10 . 212 یا 10.100.52.7:8000
        self.ip_pattern = re.compile(
            r"(?<![\d.])"
            r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"(?:\s*\.\s*(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}"
            r"(?::\d{1,5})?"
            r"(?![\d.])"
        )
        
        # جدول تبدیل اعداد فارسی و عربی به انگلیسی
        self.fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

    def process_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        vault_data = {}
        ip_map = {}
        pass_map = {}

        ip_counter = 1
        pass_counter = 1

        def mask_text(text: str) -> str:
            nonlocal ip_counter, pass_counter
            if not isinstance(text, str):
                return text

            # ۱. تبدیل اعداد فارسی به انگلیسی
            normalized_text = text.translate(self.fa_to_en)

            # ۲. ماسک کردن پسوردها
            def replace_pass(match):
                nonlocal pass_counter
                real_pass = match.group(1).strip()
                if real_pass not in pass_map:
                    placeholder = f"[SEC_PASS_{pass_counter}]"
                    pass_map[real_pass] = placeholder
                    vault_data[placeholder] = real_pass
                    pass_counter += 1
                return pass_map[real_pass]

            masked_text = self.pass_pattern.sub(replace_pass, normalized_text)

            # ۳. ماسک کردن IPها
            def replace_ip(match):
                nonlocal ip_counter
                raw_match = match.group(0)
                # حذف فاصله‌های اضافه برای ذخیره تمیز در Vault
                clean_ip = re.sub(r"\s+", "", raw_match)
                
                if clean_ip not in ip_map:
                    placeholder = f"[SEC_IP_{ip_counter}]"
                    ip_map[clean_ip] = placeholder
                    vault_data[placeholder] = clean_ip
                    ip_counter += 1
                return ip_map[clean_ip]

            masked_text = self.ip_pattern.sub(replace_ip, masked_text)
            return masked_text

        def transform_node(node):
            if isinstance(node, dict):
                return {k: transform_node(v) for k, v in node.items()}
            elif isinstance(node, list):
                return [transform_node(item) for item in node]
            elif isinstance(node, str):
                return mask_text(node)
            return node

        masked_data = transform_node(data)

        # نام‌گذاری و ذخیره فایل‌های خروجی
        parent_dir = path.parent
        stem = path.stem
        masked_path = parent_dir / f"{stem}_masked.json"
        vault_path = parent_dir / f"{stem}_vault.json"

        with open(masked_path, "w", encoding="utf-8") as f:
            json.dump(masked_data, f, ensure_ascii=False, indent=2)

        with open(vault_path, "w", encoding="utf-8") as f:
            json.dump(vault_data, f, ensure_ascii=False, indent=2)

        print(f"Masked {len(ip_map)} unique IPs, {len(pass_map)} passwords.")
        print(f"Generated: {masked_path.name} & {vault_path.name}")
        return str(masked_path), str(vault_path)
