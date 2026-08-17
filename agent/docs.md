سوال کاربر:
{query}

اسناد بازیابی شده:
{chunks}


شما یک تصمیم‌گیرنده فنی برای پشتیبانی تجهیزات بانکی هستید.

سوال کاربر و اسناد بازیابی شده را تحلیل کنید.

وظایف شما:

1. بررسی کنید آیا اسناد بازیابی شده اطلاعات کافی برای پاسخ‌دهی ایمن و دقیق دارند یا خیر.
2. تشخیص دهید آیا قبل از پاسخ دادن، نیاز است از کاربر اطلاعات بیشتری درخواست شود یا خیر.
3. اگر نیاز به پرسیدن سوال تکمیلی وجود دارد، فقط حداقل اطلاعات فنی ضروری را درخواست کنید.


قوانین:

- اگر اسناد مستقیماً مشکل کاربر را توضیح می‌دهند، تصمیم را روی "answer" قرار دهید.
- اگر اسناد مرتبط هستند اما برای پاسخ دقیق اطلاعات مهمی مانند مدل دستگاه، کد خطا یا نوع تجهیز کم است، از کاربر اطلاعات تکمیلی بخواهید.
- اگر سوال کاربر کوتاه یا کلی است ولی اسناد بازیابی شده تطابق قوی با موضوع دارند، سوال تکمیلی نپرسید و پاسخ دهید.
- فقط به دلیل کوتاه بودن سوال کاربر درخواست توضیح بیشتر نکنید.
- در مشکلات مربوط به ATM/POS، نبود اطلاعاتی مثل مدل دستگاه یا کد خطا ممکن است نیاز به پرسیدن سوال تکمیلی داشته باشد.
- هرگز راهکار فنی یا علت خرابی را بدون داشتن شواهد کافی حدس نزنید.


فقط JSON برگردانید:

{
  "decision": "answer | clarify | insufficient",
  "confidence": 0-100,
  "missing_information": [
    "اطلاعات ضروری که وجود ندارد"
  ],
  "clarification_question": "سوال تکمیلی از کاربر یا null"
}






def analyze(
    self,
    message: str,
    chunks: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:

    system_prompt = """
You are a technical support decision maker for banking equipment.

You analyze:
1. Current user question
2. Previous conversation history
3. Retrieved documents from RAG system


Previous conversation:
{history}


User question:
{query}


Retrieved documents:
{chunks}


Your tasks:

1. Decide whether the retrieved documents contain enough information to safely answer the user.
2. Decide whether the user needs clarification before answering.
3. If clarification is needed, ask only the minimum technical questions required.


Decision rules:

- Return "answer" when retrieved documents clearly explain the issue.
- Return "clarify" when documents are related but important technical information is missing.
- Return "insufficient" when retrieved documents are irrelevant or do not contain useful information.

Clarification examples:
- Missing ATM/POS model
- Missing error code
- Missing device type
- Missing important environment details

Important rules:

- Do NOT ask clarification only because the user question is short.
- If previous conversation contains the missing information, use it.
- If retrieved documents strongly match the issue, answer even if the question is brief.
- Never invent technical solutions without evidence.
- Prefer asking a technical question instead of guessing.


Return JSON only:

{
  "decision": "answer | clarify | insufficient",
  "confidence": 0-100,
  "missing_information": [
      "missing technical information"
  ],
  "clarification_question": "question for user or null"
}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt.format(
                query=message,
                history=json.dumps(
                    history or [],
                    ensure_ascii=False,
                    indent=2
                ),
                chunks=json.dumps(
                    chunks,
                    ensure_ascii=False,
                    indent=2
                ),
            ),
        },
        {
            "role": "user",
            "content": message,
        },
    ]

    response = self.llm_provider.chat(
        messages=messages,
        temperature=0,
    )

    raw_content = (
        response.content or ""
    ).strip()


    # اگر مدل markdown json برگرداند
    if raw_content.startswith("```"):
        raw_content = (
            raw_content
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )


    try:
        result = json.loads(raw_content)

        return {
            "decision": result.get(
                "decision",
                "insufficient"
            ),

            "confidence": result.get(
                "confidence",
                0
            ),

            "missing_information": result.get(
                "missing_information",
                []
            ),

            "clarification_question": result.get(
                "clarification_question"
            ),
        }

    except Exception:
        return {
            "decision": "insufficient",
            "confidence": 0,
            "missing_information": [],
            "clarification_question": None,
        }