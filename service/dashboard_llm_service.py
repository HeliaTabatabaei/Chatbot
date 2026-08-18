import json
import re
from typing import Any, Callable, Dict

from SQlDB.DashboardQuery import run_sql
from prompt_Config_Dashboard import CALENDAR, EXAMPLES, METRICS, SCHEMA

class dashboard_llm_service:
    
    system_prompt = """
    شما یک تحلیلگر داده برای داشبورد هستید.
    
    قوانین پاسخ:
    - پاسخ را فقط به زبان فارسی بنویس.
    - فقط بر اساس داده‌های ارائه‌شده پاسخ بده.
    - هیچ عدد، نتیجه یا تحلیلی خارج از داده‌ها نساز.
    - پاسخ کوتاه، دقیق و قابل‌فهم باشد.
    - از اصطلاحات فنی غیرضروری استفاده نکن.
    """.strip()
    SYNONYM_MAP = {
        "Wincor": ["wincor", "wincore", "وینکور"],
        "NCR": ["ncr", "ان سی آر", "انسیار"],
        "ATM": ["atm", "خودپرداز"],
        "CRS": ["crs", "خوددریافت", "cash recycler"]
    }
    def __init__(self, llm):
        self.llm = llm

  
    def normalize_text(self,text: str) -> str:
        replacements = {
        "ي": "ی",
        "ك": "ک",
    }

        for source, target in replacements.items():
            text = text.replace(source, target)

        return " ".join(text.strip().split())
    def replace_synonyms(self,text: str) -> str:
        text = self.normalize_text(text)

        for standard, synonyms in self.SYNONYM_MAP.items():
            for word in synonyms:
                pattern = r"\b" + re.escape(word) + r"\b"
                text = re.sub(
                    pattern,
                    standard,
                    text,
                    flags=re.IGNORECASE
                )

        return text
    def generate_sql(self,user_question: str) -> str:
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
        response = self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            
        )
        return response.content.strip()

    def generate_answer_stream(
        self,
        question: str,
        data: list[Dict],
        on_chunk: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        پاسخ فارسی را به صورت stream از LLM دریافت می‌کند.
        """

        # در نبود داده، فراخوانی LLM لازم نیست.
        if not data:
            on_chunk({
                "type": "token",
                "content": "متأسفانه داده‌ای برای این پرسش پیدا نشد."
            })
            return

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
""".strip()

        self.llm.chat_stream(
            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            on_chunk=on_chunk,
            temperature=0.2,
        )
    def ask(self, question: str) -> Dict[str, Any]:
        # """
        # پردازش کامل سؤال داشبورد:
        # 1. تولید SQL با LLM
        # 2. اعتبارسنجی امنیت SQL
        # 3. اجرای SQL
        # 4. تولید پاسخ فارسی بر اساس داده‌ها

        # Args:
        #     question (str): سؤال کاربر.

        # Returns:
        #     dict: سؤال، SQL تولیدشده، داده خام و پاسخ نهایی.
        # """

        # 1) تولید SQL
        sql_query = self.generate_sql(question)

        # 2) اعتبارسنجی SQL پیش از اجرا
        # self.validate_sql(sql_query)

        # 3) اجرای SQL و دریافت داده‌ها
        data = self.run_sql(sql_query)

        # 4) تولید پاسخ فارسی
        answer = self.generate_answer(question, data)

        return {
            "question": question,
            "sql": sql_query,
            "data": data,
            "answer": answer
        }

    # def generate_sql(self, user_question: str) -> str:
    #     """
    #     تولید SQL از روی سؤال کاربر
    #     """
    #     return generate_sql(
            
    #         user_question=user_question
    #     )

    def run_sqlQuery(self, sql_query: str):
        """
        اجرای SQL و دریافت داده
        """
        return run_sql(sql_query)

    def generate_answer(self, question: str, data):
        """
        تولید پاسخ فارسی بر اساس داده‌های SQL
        """
        return self.generate_answer(
         
            question=question,
            data=data
        )

    # def validate_sql(self, sql_query: str) -> None:
    #     """
    #     اعتبارسنجی SQL قبل از اجرا
    #     """
    #     validate_sql(sql_query)