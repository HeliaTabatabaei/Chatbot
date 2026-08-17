from datetime import datetime
import traceback

from SQlDB.db import DatabaseConnection
from config import connection_string


def InsertIntoWallet(total_tokens, output_tokens, input_tokens, user_key, llm_response_id):
    try:
        print(connection_string)

        with DatabaseConnection(connection_string) as cursor:
            query = """
                INSERT INTO [LLMDB].[dbo].[WalletTransaction]
                    ([amount]
                    ,[outputToken]
                    ,[inputToken]
                    ,[userkey]
                    ,[createdTime]
                    ,[TypeTransaction]
                    ,[requstid])
                VALUES (?, ?, ?, CAST(? AS uniqueidentifier), ?, ?, ?)
            """

            params = (
                total_tokens,
                output_tokens,
                input_tokens,
                user_key,
                datetime.now(),
                2,
                str(llm_response_id) if llm_response_id is not None else None
            )

            cursor.execute(query, params)

    except Exception as e:
        print(f"Error InsertIntoWallet: {e}", flush=True)
        traceback.print_exc()
