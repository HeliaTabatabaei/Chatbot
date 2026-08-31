from Utility.Security import SensitiveDataMasker
from pathlib import Path

masker = SensitiveDataMasker()
BASE_DIR = Path(__file__).resolve().parent

# ۲. ساخت مسیر به صورت استاندارد
file_path = BASE_DIR / "data" / "1-IT0410-517-04_SamanSoft_Win10" / "1.json"

masked_path, vault_path = masker.process_file(file_path)
print(f"✅ فایل ماسک‌شده ذخیره شد در: {masked_path}")
print(f"🔐 فایل کلیدها ذخیره شد در:   {vault_path}")

