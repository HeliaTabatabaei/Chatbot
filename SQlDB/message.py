from datetime import datetime
import traceback

from SQlDB.db import DatabaseConnection
from config import connection_string

def update_and_get_bank_name(chat_id, bank_name):
    """
    اگر نام بانک جدید داشتیم آپدیت کن، در هر صورت نام بانک فعلی رو برگردون
    """
    try:
        with DatabaseConnection(connection_string) as cursor:
            # ۱. اگر نام بانک جدید پیدا شده، اول آپدیت کن
            if bank_name:
                clean_name = bank_name.strip()
                update_query = """
                    UPDATE [LLMDB].[dbo].[Conversations]
                    SET [BankName] = ?
                    WHERE [chatId] = CAST(? AS uniqueidentifier)
                """
                cursor.execute(update_query, (clean_name, str(chat_id)))

            # ۲. حالا نام بانک رو بخون (چه آپدیت شده باشه چه از قبل بوده باشه)
            select_query = """
                SELECT [BankName] 
                FROM [LLMDB].[dbo].[Conversations] 
                WHERE [chatId] = CAST(? AS uniqueidentifier)
            """
            cursor.execute(select_query, (str(chat_id),))
            result = cursor.fetchone()
            
            # برگرداندن مقدار واقعی یا None (بدون رشته "None")
            return result[0] if (result and result[0]) else None

    except Exception as e:
        print(f"Error update_and_get_bank_name: {e}", flush=True)
        return None
