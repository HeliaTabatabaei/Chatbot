from datetime import datetime
import traceback

from SQlDB.db import DatabaseConnection
from config import connection_string

def updateClarifyMessage(bankName, conversationID):
    try:
        with DatabaseConnection(connection_string) as cursor:
            query = """
                UPDATE [dbo].[Conversations]
                SET [bankName] = ?
                WHERE [chatId] = ?
            """

            params = (bankName, conversationID)
            cursor.execute(query, params)

    except Exception as e:
        print(f"Error updateClarifyMessage: {e}", flush=True)
        traceback.print_exc()
def getClarifyBankName(conversationID):
    try:
        with DatabaseConnection(connection_string) as cursor:
            query = """
                SELECT TOP 1 [bankName]
                FROM [dbo].[Conversations]
                WHERE [chatId] = ?
            """

            cursor.execute(query, (conversationID,))
            row = cursor.fetchone()

            if row is None:
                return None

            return row[0]

    except Exception as e:
        print(f"Error getClarifyBankName: {e}", flush=True)
        traceback.print_exc()
        return None    