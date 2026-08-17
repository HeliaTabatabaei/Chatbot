import re
# from langchain_openai import ChatOpenAI
from providers.factory import create_provider
import json

from config import EMBED_MODEL, OPENAI_API_KEY,LLM_MODEL
from prompt_Config_Dashboard import SCHEMA, METRICS, CALENDAR, EXAMPLES

SYNONYM_MAP = {
    "Wincor": ["wincor", "wincore", "وینکور"],
    "NCR": ["ncr", "ان سی آر", "انسیار"],
    "ATM": ["atm", "خودپرداز"],
    "CRS": ["crs", "خوددریافت", "cash recycler"]
}


def normalize_text(text: str) -> str:
    replacements = {
        "ي": "ی",
        "ك": "ک",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    return " ".join(text.strip().split())


def replace_synonyms(text: str) -> str:
    text = normalize_text(text)

    for standard, synonyms in SYNONYM_MAP.items():
        for word in synonyms:
            pattern = r"\b" + re.escape(word) + r"\b"
            text = re.sub(
                pattern,
                standard,
                text,
                flags=re.IGNORECASE
            )

    return text


llm = create_provider(
    provider_name="openai",
    base_uri="https://api.gapgpt.app/v1",
    api_key=OPENAI_API_KEY,
    model=LLM_MODEL,
    embed_model=EMBED_MODEL,
)


#سوال کاربر به مدل داده میشود یه رشته اسکیوال برمیگرده
def generate_sql(llm,user_question: str) -> str:
    DEVICE_TYPE_MAPPING = """
          Device Type Normalization:
         - ATM: خودپرداز, عابربانک, ATM
         - CRS: سی‌آر‌اس, CRS, خوددریافت-خودپرداز
         - Cash Acceptor: اسکناس‌پذیر, پول‌پذیر, Cash Acceptor, پذیرش وجه
         - Kiosk: کیوسک, Kiosk
         - Scanner: اسکنر, Scanner
         - MultiMedia: مالتی‌مدیا, MultiMedia, Multimedia, چندرسانه‌ای
         """
    system_prompt = f"""
You are an expert SQL Server analyst.

Your task is to generate one safe SQL Server SELECT query
based on a Persian user question.
{DEVICE_TYPE_MAPPING}
Strict rules:
- Only generate one SELECT query.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, MERGE, CREATE, TRUNCATE.
- Use SQL Server syntax.
- Return only raw SQL. No markdown. No explanation.
- Do not use JOIN unless it is absolutely required by the metric definition.
- Use ai_request_analysis for failures(خرابی), service requests (سرویس), cancellations, and delay metrics.
- Use ai_GetDeviceCount for device counts (تعداد دستگاه) and device statistics.
- For AreaTitle filtering always use LIKE with N'%' wildcards.
- For DeviceType filtering always use LIKE with N'%' wildcards.
- For normal failure count, exclude cancelled requests using IsCancel = 0.
- Use TOP only when the user explicitly requests ranking/top results.

Schema:
{SCHEMA}

Metrics:
{METRICS}

Calendar:
{CALENDAR}

Examples:
{EXAMPLES}

User Question:
{user_question}


"""
    user_prompt = f"User Question: {user_question}\nSQL:"
    response = llm.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        
    )
    return response.content.strip()

# بعد از اجرای اسکیوال جواب در قالب دیکشنری به این تابع میآید تا ال ال ام پاسخ شفاف تری بده
def generate_answer(llm,question: str, data: list[dict]) -> str:
    """
    بر اساس سؤال کاربر و داده‌های برگشتی از SQL Server،
    یک پاسخ فارسی، کوتاه و قابل‌فهم تولید می‌کند.

    Args:
        question (str): سؤال اصلی کاربر.
        data (list[dict]): نتیجه اجرای SQL به‌صورت لیستی از دیکشنری‌ها.

    Returns:
        str: پاسخ نهایی فارسی برای نمایش به کاربر.
    """

    # اگر SQL هیچ داده‌ای برنگرداند، نیازی به فراخوانی LLM نداریم.
    if not data:
        return "متأسفانه داده‌ای برای این پرسش پیدا نشد."

    system_prompt = """
        شما یک تحلیلگر داده برای داشبورد هستید.

        قوانین پاسخ:
        - پاسخ را فقط به زبان فارسی بنویس.
        - فقط بر اساس داده‌های ارائه‌شده پاسخ بده.
        - هیچ عدد، نتیجه یا تحلیلی خارج از داده‌ها نساز.
        - پاسخ کوتاه، دقیق و قابل‌فهم باشد.
        - از اصطلاحات فنی غیرضروری استفاده نکن.
        """

    # ensure_ascii=False مهم است تا متن فارسی به شکل \\u06xx ارسال نشود.
    data_json = json.dumps(data, ensure_ascii=False, default=str)#لیستی از دیکشنری ها به رشته تبدیل میشود
    user_prompt = f"""
    سؤال کاربر:
    {question}

    داده‌های استخراج‌شده از دیتابیس:
    {data_json}

    بر اساس داده‌های بالا به سؤال کاربر پاسخ بده.
    """

    response = llm.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2
    )

    return response.content.strip()
import json
from typing import Any, Callable


def generate_answer_stream(
    llm,
    question: str,
    data: list[dict],
    on_chunk: Callable[[dict[str, Any]], None],
) -> None:
    """
    پاسخ فارسی را به صورت stream از LLM دریافت می‌کند.

    هر token یا meta از طریق on_chunk به لایه بالاتر ارسال می‌شود.

    نمونه token:
        {"type": "token", "content": "تعداد خرابی‌ها "}

    نمونه meta:
        {
            "type": "meta",
            "response_id": "...",
            "usage": {...}
        }
    """

    # در نبود داده، فراخوانی LLM لازم نیست.
    if not data:
        on_chunk({
            "type": "token",
            "content": "متأسفانه داده‌ای برای این پرسش پیدا نشد."
        })
        return

    system_prompt = """
شما یک تحلیلگر داده برای داشبورد هستید.

قوانین پاسخ:
- پاسخ را فقط به زبان فارسی بنویس.
- فقط بر اساس داده‌های ارائه‌شده پاسخ بده.
- هیچ عدد، نتیجه یا تحلیلی خارج از داده‌ها نساز.
- پاسخ کوتاه، دقیق و قابل‌فهم باشد.
- از اصطلاحات فنی غیرضروری استفاده نکن.
"""

    # تبدیل خروجی SQL Server به JSON قابل‌فهم برای مدل
    data_json = json.dumps(
        data,
        ensure_ascii=False,
        default=str,
    )

    user_prompt = f"""
سؤال کاربر:
{question}

داده‌های استخراج‌شده از دیتابیس:
{data_json}

فقط بر اساس داده‌های بالا پاسخ بده.
"""

    # chat_stream در OpenAIProvider شما:
    # - stream=True را به API می‌فرستد.
    # - هر بخش از متن را با on_chunk برمی‌گرداند.
    # - در پایان meta شامل usage را ارسال می‌کند.
    llm.chat_stream(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        on_chunk=on_chunk,
        temperature=0.2,
    )
