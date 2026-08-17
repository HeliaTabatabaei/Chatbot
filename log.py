import datetime
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "qa_log.txt"
LOG_FILEtest = LOG_DIR / "qa_log1.txt"
def append_qa_to_file(question: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with LOG_FILE.open("a", encoding="utf-8") as f:
            # f.write("=" * 80 + "\n")
            # f.write(f"Time: {timestamp}\n")
            f.write(f"Q: {question}\n")
          

        print(f"QA log saved at: {LOG_FILE}", flush=True)

    except Exception as e:
        print(f"Failed to save QA log: {repr(e)}", flush=True)  
def append_qa_to_filetest(question: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with LOG_FILEtest.open("a", encoding="utf-8") as f:
            # f.write("=" * 80 + "\n")
            # f.write(f"Time: {timestamp}\n")
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
        # print(f"پیام با موفقیت در '{log_file}' ثبت شد.") # در صورت نیاز، پیام موفقیت را نمایش دهید
    except Exception as e:
        print(f"خطا در ثبت لاگ در فایل '{log_file}': {e}")

# --- مثال نحوه استفاده ---
if __name__ == "__main__":
   append_qa_to_file("tttttt")