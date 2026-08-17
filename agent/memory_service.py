from typing import Optional, Tuple
import uuid

from SQlDB.db import DatabaseConnection
from dbManagement import SQL_SERVER_CONNECTION_STRING, get_conversation_history, save_conversation, save_message


class MemoryService:

    
    def normalize_conversation_id(conversation_id: Optional[str]) -> Tuple[str, bool]:
      
        try:
            if conversation_id is None:
                raise ValueError

            conversation_id = str(conversation_id).strip()

            if conversation_id in ("", "undefined", "null", "None"):
                raise ValueError

            normalized = str(uuid.UUID(conversation_id))
            return normalized, False

        except (ValueError, TypeError, AttributeError):
            return str(uuid.uuid4()), True


    def get_recent_history(
       
        conversation_id: str,
        query:str,
        user_key:str,
        limit: int = 3
    ):
        conversation_id, is_new_chat = self.normalize_conversation_id(conversation_id)
        
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
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])