from datetime import datetime
from typing import List, Optional
import uuid
from LLM.OpenAIManagment import createSummery
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


def update_conversation_summary_task(conversation_id: str, new_user_msg: str, new_assistant_msg: str):
    """
    این تابع در پس‌زمینه اجرا می‌شود و خلاصه مکالمه را به‌روز می‌کند.
    """
    try:
        with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as cursor:
            # ۱. دریافت خلاصه قبلی از دیتابیس
            cursor.execute("SELECT Summary FROM dbo.Conversations WHERE chatId = ?", (conversation_id,))
            row = cursor.fetchone()
            old_summary = row[0] if row and row[0] else "مکالمه به تازگی شروع شده است."

            # # ۲. ساخت پرامپت برای مدل خلاصه‌ساز
            # summary_prompt = f"""
            # با توجه به خلاصه قبلی مکالمه و پیام‌های جدید مبادله شده، یک خلاصه کوتاه، جامع و به زبان فارسی از کل مکالمه تا این لحظه بنویس. 
            # جزئیات فنی مهم (مانند نام ابزارها، پورت‌ها، خطاها یا تصمیمات کلیدی) را حفظ کن اما خلاصه را تا حد امکان فشرده نگه‌دار.

            # خلاصه قبلی:
            # {old_summary}

            # پیام‌های جدید:
            # کاربر: {new_user_msg}
            # دستیار: {new_assistant_msg}

            # خلاصه جدید به‌روزشده:
            # """
            
            # ۳. فراخوانی مدل برای خلاصه‌سازی (یک مدل سبک‌تر و سریع‌تر ترجیح داده می‌شود)
            # response = client.responses.create(
            #     model=LLM_MODEL,  # یا یک مدل سریع‌تر/ارزان‌تر
            #     input=[{"role": "user", "content": summary_prompt}],
            #     temperature=0.3
            # )
            new_summary =createSummery(old_summary,new_user_msg,new_assistant_msg) #response.output_text.strip()

            # ۴. ذخیره خلاصه جدید در دیتابیس
            cursor.execute(
                "UPDATE dbo.Conversations SET Summary = ? WHERE chatId = ?",
                (new_summary, conversation_id)
            )
            
    except Exception as e:
        print(e)
        # اینجا لاگ خطا را ثبت کنید تا در صورت بروز مشکل، جریان اصلی چت متوقف نشود
        #(f"Error updating summary for {conversation_id}: {str(e)}")

def save_assistant_message_task(conv_id, ans, resp_id):
    with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as bg_cursor:
        save_message(
            cursor=bg_cursor,
            conversation_id=conv_id,
            role="assistant",
            content=ans,
            provider_response_id=resp_id
        )
