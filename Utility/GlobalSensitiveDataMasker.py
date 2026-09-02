import os
import re
import json
from pathlib import Path
from typing import Union

class GlobalSensitiveDataMasker:
    def __init__(self, vault_file_path: Union[str, Path]):
        self.vault_path = Path(vault_file_path).resolve()
        
        # الگوهای تشخیص رمز و IP
        self.pass_pattern = re.compile(r"\{\{SECRET_PASS:(.*?)\}\}")
        self.ip_pattern = re.compile(
            r"(?<![\d.])"
            r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"(?:\s*\.\s*(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}"
            r"(?::\d{1,5})?"
            r"(?![\d.])"
        )
        self.fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧۸۹", "01234567890123456789")

        self.vault_data = {}
        self.ip_map = {}
        self.pass_map = {}
        self.ip_counter = 1
        self.pass_counter = 1
        
        self._load_existing_vault()

    def _load_existing_vault(self):
        if self.vault_path.exists():
            try:
                with open(self.vault_path, "r", encoding="utf-8") as f:
                    self.vault_data = json.load(f)

                for placeholder, real_val in self.vault_data.items():
                    if placeholder.startswith("[SEC_IP_"):
                        self.ip_map[real_val] = placeholder
                        num_match = re.search(r"\d+", placeholder)
                        if num_match:
                            num = int(num_match.group())
                            if num >= self.ip_counter:
                                self.ip_counter = num + 1
                    elif placeholder.startswith("[SEC_PASS_"):
                        self.pass_map[real_val] = placeholder
                        num_match = re.search(r"\d+", placeholder)
                        if num_match:
                            num = int(num_match.group())
                            if num >= self.pass_counter:
                                self.pass_counter = num + 1
            except Exception as e:
                print(f"[Warning] Could not load vault: {e}")

    def _save_vault(self):
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump(self.vault_data, f, ensure_ascii=False, indent=2)

    def mask_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        normalized_text = text.translate(self.fa_to_en)

        def replace_pass(match):
            real_pass = match.group(1).strip()
            if real_pass not in self.pass_map:
                placeholder = f"[SEC_PASS_{self.pass_counter}]"
                self.pass_map[real_pass] = placeholder
                self.vault_data[placeholder] = real_pass
                self.pass_counter += 1
            return self.pass_map[real_pass]

        masked_text = self.pass_pattern.sub(replace_pass, normalized_text)

        def replace_ip(match):
            clean_ip = re.sub(r"\s+", "", match.group(0))
            if clean_ip not in self.ip_map:
                placeholder = f"[SEC_IP_{self.ip_counter}]"
                self.ip_map[clean_ip] = placeholder
                self.vault_data[placeholder] = clean_ip
                self.ip_counter += 1
            return self.ip_map[clean_ip]

        masked_text = self.ip_pattern.sub(replace_ip, masked_text)
        return masked_text

    def _transform_node(self, node):
        if isinstance(node, dict):
            return {k: self._transform_node(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [self._transform_node(item) for item in node]
        elif isinstance(node, str):
            return self.mask_text(node)
        return node

    def process_file(self, file_path: Union[str, Path]) -> str:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        masked_data = self._transform_node(data)

        # ساخت فایل _masked دقیقاً در همان پوشه کنار فایل اصلی
        masked_path = path.parent / f"{path.stem}_masked.json"

        with open(masked_path, "w", encoding="utf-8") as f:
            json.dump(masked_data, f, ensure_ascii=False, indent=2)

        # ذخیره Vault مشترک در روت data
        self._save_vault()

        return str(masked_path)
