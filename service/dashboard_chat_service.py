
# from .dashboard_llm_service import generate_answer
from .dashboard_llm_service import generate_answer,generate_sql
from SQlDB.DashboardQuery import run_sql
# from SQlDB.sql_validator import validate_sql


def ask(llm, question: str) -> dict:
    """
    پردازش کامل سؤال داشبورد:
    1. تولید SQL با LLM
    2. اعتبارسنجی امنیت SQL
    3. اجرای SQL
    4. تولید پاسخ فارسی بر اساس داده‌ها

    Args:
        provider: نمونه Provider ساخته‌شده با create_provider.
        question (str): سؤال کاربر.

    Returns:
        dict: سؤال، SQL تولیدشده، داده خام و پاسخ نهایی.
    """

    # 1) تولید SQL
    sql_query = generate_sql(
        llm=llm,
        user_question=question
    )

    # 2) اعتبارسنجی SQL پیش از اجرا
    # validate_sql(sql_query)

    # 3) اجرای SQL و دریافت داده‌ها
      # برای مشاهده SQL تولیدشده قبل از اجرای آن
    # print("\n" + "=" * 60)
    # print("GENERATED SQL:")
    # print(sql_query)
    # print("=" * 60 + "\n")
    data = run_sql(sql_query)

    # 4) تولید پاسخ فارسی
    answer = generate_answer(
        llm=llm,
        question=question,
        data=data
    )

    return {
        "question": question,
        "sql": sql_query,
        "data": data,
        "answer": answer
    }
