import json
import re
from typing import Any, Callable, Dict

from SQlDB.DashboardQuery import run_sql
from Prompt.prompt_Config_Dashboard import CALENDAR, EXAMPLES, METRICS, SCHEMA

class dashboard_llm_service:
    
    system_prompt = """
    شما یک تحلیلگر داده برای داشبورد هستید.
    
    قوانین پاسخ:
    1- پاسخ را فقط به زبان فارسی بنویس.
    2- فقط بر اساس داده‌های ارائه‌شده پاسخ بده.
    3- هیچ عدد، نتیجه یا تحلیلی خارج از داده‌ها نساز.
    4- پاسخ کوتاه، دقیق و قابل‌فهم باشد.
    5- در صورتی که داده‌ها شامل ستون‌های MTD و FullMonth (مقایسه هم‌دوره سال گذشته) بودند، پاسخ را دقیقاً در دو بخش مجزا و خوانا بنویسید:
    - عملکرد تا روز معادل امروز در سال گذشته (MTD): شامل تعداد کل خرابی، تعداد تکراری و نرخ خرابی تکراری (درصد).
    - عملکرد در کل ماه سال گذشته (Full Month): شامل تعداد کل خرابی، تعداد تکراری و نرخ خرابی تکراری (درصد).
    6- از اصطلاحات فنی غیرضروری استفاده نکن.
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

            Generate one single SELECT statement (no multiple statements, no GO).
            If the question refers to a month-based metric of the previous year, this single SELECT must return BOTH series of columns: *_MTD and *_FullMonth.

            based on a Persian user question.
            {DEVICE_TYPE_MAPPING}
            Strict rules:
            - Return valid T-SQL (you may declare variables using dbo.ai_CurrentDateContext before the final SELECT).
            - Never generate INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, MERGE, CREATE, TRUNCATE.
            - Use SQL Server syntax.
            - Return only raw SQL. No markdown. No explanation.
            - Do not use JOIN unless it is absolutely required by the metric definition.
            - Use ai_request_analysis for failures(خرابی), service requests (سرویس), cancellations, and delay metrics.
            - Use ai_GetDeviceCount for device counts (تعداد دستگاه) and device statistics.
            - Resolve office names using AreaTitle with LIKE N'%name%' wildcards (e.g., @MainAreaId = Area_Id of the matched office).
            - In dbo.ai_request_analysis, filter offices with (Area_Id = @MainAreaId OR ParentId = @MainAreaId) so satellite offices are included. 
            - Do NOT use Area_Id/ParentId in dbo.ai_GetDeviceCount — that view uses AreaId instead.
            - You may only use Area_Id / ParentId columns on the table dbo.ai_request_analysis.
            - Never use Area_Id on any other table or view (e.g. ai_GetDeviceCount does not have it).

            - In dbo.ai_GetDeviceCount the column name is [AreaId] (or filter by AreaTitle if applicable).
            - Do NOT use Area_Id on views that do not have it.


            - For DeviceType filtering always use LIKE with N'%' wildcards.
            - For normal failure count, exclude cancelled requests using IsCancel = 0.
            - Use TOP only when the user explicitly requests ranking/top results.
            Year-over-Year (YoY) same month rule (e.g. شهریور پارسال when current month is شهریور):
            - Read PreviousPersianYear, CurrentPersianMonth, CurrentPersianDay from dbo.ai_CurrentDateContext.
            - Set @StartDate = PrevYear + Month + '01'.
            - Set @EndDateMTD = PrevYear + Month + CurrentDay.
            - Set @EndDateFull = PrevYear + Month + (Last Day of Month: 31/30/29).
            - Main query WHERE clause must use `BETWEEN @StartDate AND @EndDateFull`.
            - Calculate MTD metrics using `CASE WHEN InsertedDate <= @EndDateMTD THEN ... END`.
            - Calculate FullMonth metrics across the whole range without date filter inside CASE.
            - ALWAYS use COUNT(DISTINCT DeviceID) when counting devices from dbo.ai_GetDeviceCount. NEVER write COUNT(DeviceID) without DISTINCT.
            - ALWAYS use COUNT(DISTINCT Requests_Id) when counting requests.

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