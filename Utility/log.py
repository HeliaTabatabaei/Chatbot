import datetime
import os
from pathlib import Path
from typing import Optional
from config import logstatus

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "qa_log.txt"
LOG_FILEtest = LOG_DIR / "qa_log1.txt"
def append_qa_to_file(question: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with LOG_FILE.open("a", encoding="utf-8") as f:
           
            f.write(f"Q: {question}\n")
          

        print(f"QA log saved at: {LOG_FILE}", flush=True)

    except Exception as e:
        print(f"Failed to save QA log: {repr(e)}", flush=True)  

        
def append_qa_to_fileWithConvertion(question: str, ConvertionID: Optional[str] = None) -> None:
    
    if str(logstatus).strip() in ("1", "true", "True"):
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)

            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # در صورت نبودن ID، مقدار پیش‌فرض قرار می‌دهیم
            safe_conv_id = ConvertionID if ConvertionID else "default"

            # ۱. نام فایل: ترکیب تاریخ روز و Conversation ID
            log_file_name = f"{today_str}_{safe_conv_id}.log"
            target_log_file = LOG_DIR / log_file_name

            # ۲. پاک‌سازی خودکار لاگ‌های بیش از ۷ روز گذشته
            one_week_ago = (now - datetime.timedelta(days=0)).date()
            
            for old_file in LOG_DIR.glob("*.log"):
                try:
                    # جدا کردن تاریخ از ابتدای نام فایل (فرمت YYYY-MM-DD_*)
                    file_date_part = old_file.stem.split("_")[0]
                    file_date = datetime.datetime.strptime(file_date_part, "%Y-%m-%d").date()
                    
                    if file_date < one_week_ago:
                        old_file.unlink()  # حذف فایل قدیمی
                        print(f"Deleted old log file: {old_file.name}", flush=True)
                except (ValueError, IndexError):
                    # اگر فایلی فرمت نام‌گذاری دیگری داشت رد شو تا خطایی رخ ندهد
                    continue

            # ۳. ثبت لاگ پرسش
            with target_log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] Q: {question}\n")

            print(f"QA log saved at: {target_log_file}", flush=True)

        except Exception as e:
            print(f"Failed to save QA log: {repr(e)}", flush=True)            
def append_qa_to_filetest(question: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with LOG_FILEtest.open("a", encoding="utf-8") as f:
          
            f.write(f"Q: {question}\n")
          

      

    except Exception as e:
        print(f"Failed to save QA log: {repr(e)}", flush=True)          
def log_message(message: str, log_file: str = "app_log.txt"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    try:
        # اگر فایل لاگ وجود نداشت، آن را ایجاد می‌کنیم
        if not os.path.exists(log_file):
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(log_entry)
        else:
            # در غیر این صورت، پیام را به انتهای فایل اضافه می‌کنیم
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
       
    except Exception as e:
        print(f"خطا در ثبت لاگ در فایل '{log_file}': {e}")


if __name__ == "__main__":
   append_qa_to_file("tttttt")