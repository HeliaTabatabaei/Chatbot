from datetime import datetime
import traceback

from SQlDB.db import DatabaseConnection
from config import connection_string
def InsertIntoWallet(total_tokens, output_tokens, input_tokens, user_key, llm_response_id, Provider, State):
    try:
        with DatabaseConnection(connection_string) as cursor:
            query = """
                INSERT INTO [LLMDB].[dbo].[WalletTransaction]
                    ([amount]
                    ,[outputToken]
                    ,[inputToken]
                    ,[userkey]
                    ,[createdTime]
                    ,[TypeTransaction]
                    ,[requstid]
                    ,[Provider]
                    ,[State])
                VALUES (?, ?, ?, CAST(? AS uniqueidentifier), ?, ?, ?, ?, ?)
            """

            # اصلاح: اضافه کردن Provider و State به انتهای لیست پارامترها
            params = (
                total_tokens,
                output_tokens,
                input_tokens,
                user_key,
                datetime.now(),
                2,  # TypeTransaction
                str(llm_response_id) if llm_response_id is not None else None,
                Provider,
                State
            )

            cursor.execute(query, params)

    except Exception as e:
        print(f"Error InsertIntoWallet: {e}", flush=True)
        traceback.print_exc()
