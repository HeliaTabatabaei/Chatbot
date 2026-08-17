
from SQlDB.db import DatabaseConnection

from config import connection_string_Dashboard

def run_sql(query: str) -> list[dict]:
    """
    اجرای Query از نوع SELECT و تبدیل خروجی به لیست دیکشنری.
    
    نمونه خروجی:
    [
        {"OfficeName": "دفتر تهران", "DeviceCount": 25},
        {"OfficeName": "دفتر اصفهان", "DeviceCount": 12}
    ]
    """
    # cursor.execute("SELECT DB_NAME() AS CurrentDatabase")
    # current_db = cursor.fetchone()[0]
    # print(f"Connected database: {current_db}")
    # print("SQL to execute:")
    # print(query)
    with DatabaseConnection(connection_string_Dashboard) as cursor:
        cursor.execute(query)

        # در صورتی که Query خروجی جدولی داشته باشد
        if cursor.description is None:
            return []

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        # هر ردیف به یک دیکشنری تبدیل می‌شود تا برای LLM قابل ارسال باشد
        return [
            dict(zip(columns, row))
            for row in rows
        ]
        
        


