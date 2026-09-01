from datetime import datetime
from typing import List, Optional
import uuid

from Utility.utiliy import normalize_conversation_id
from config import connection_string
from SQlDB.db import DatabaseConnection  

SQL_SERVER_CONNECTION_STRING =connection_string
def save_conversation(cursor, conversation_id: str, title: str, user_key: Optional[str] = None, model_id: Optional[str] = None) -> str:
    # تبدیل و نرمال‌سازی
    conversation_guid = str(uuid.UUID(conversation_id))
    
    cursor.execute(
        """
        INSERT INTO dbo.Conversations (chatId, Title, Userkey, modelId, createDate)
        VALUES (?, ?, ?, ?, ?)
        """,
        (conversation_guid, title[:255], user_key, model_id, datetime.now())
    )
    return conversation_guid 

def save_message(cursor, conversation_id: str, role: str, content: str, provider_response_id: Optional[int] = None):
    cursor.execute(
        """
        INSERT INTO dbo.Messages (ConversationId, role, content, providerResponseId, createDate)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(uuid.UUID(conversation_id)),
            role,
            content,
            provider_response_id,
            datetime.now()
        )
    )
    
def get_conversation_history(cursor, conversation_id: str, limit: int = 6):
    cursor.execute(
        """
        SELECT TOP (?) role, content
        FROM (
            SELECT TOP (?) role, content, createDate, Id
            FROM dbo.Messages
            WHERE ConversationId = ?
            ORDER BY createDate DESC, Id DESC
        ) AS recent
        ORDER BY createDate ASC, Id ASC
        """,
        (limit, limit, str(uuid.UUID(conversation_id)))
    )
    rows = cursor.fetchall()
    return [{"role": row.role, "content": row.content} for row in rows]


def save_assistant_message_task(conv_id, ans, resp_id):
    with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as bg_cursor:
        save_message(
            cursor=bg_cursor,
            conversation_id=conv_id,
            role="assistant",
            content=ans,
            provider_response_id=resp_id
        )
def get_recent_history(
        
        conversation_id: str,
        query:str,
        user_key:str,
        limit: int = 6
    ):
        conversation_id, is_new_chat = normalize_conversation_id(conversation_id)

        
        with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as cursor:
            if not is_new_chat:
                cursor.execute(
                    "SELECT 1 FROM dbo.Conversations WHERE chatId = ?",
                    (conversation_id,)
                )
                if not cursor.fetchone():
                    is_new_chat = True


            if is_new_chat:
                conversation_id=save_conversation(
                    cursor=cursor,
                    conversation_id=conversation_id,
                    title=query,
                    user_key=user_key,
                    model_id=1
                )

            history = get_conversation_history(
                cursor=cursor,
                conversation_id=conversation_id,
                limit=6
            )

            save_message(
                cursor=cursor,
                conversation_id=conversation_id,
                role="user",
                content=query
            )
            # "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
            return history,conversation_id
