from datetime import datetime, timezone
import json
import os
from typing import List, Optional
from SQlDB.db import DatabaseConnection
from config import connection_string
import pyodbc
import traceback

# def LogStatus(_DocID, _ActionName, _FileName, _Step, _Status, _ErrorMessage, _Timestamp):


#     try:
#         if _Timestamp is None:
#             _Timestamp = datetime.now()

#         # conn = pyodbc.connect(connection_string)
#         # cursor = conn.cursor()
#         with DatabaseConnection(connection_string) as cursor:
#             print(f"LogStatus => DocID={_DocID}, Action={_ActionName}, Step={_Step}, Status={_Status}")

#         # اگر نام فایل پاس نشده، از جدول بخوان
#             if not _FileName and _DocID != -1:
#                 cursor.execute("""
#                     SELECT Title
#                     FROM [LLMDB].[dbo].[LLM_Documnts]
#                     WHERE id = ?
#                 """, (_DocID,))

#                 row = cursor.fetchone()
#                 _FileName = row[0] if row else None

#         # اگر باز هم FileName نداشتیم
#         if not _FileName:
#             _FileName = "Unknown"

#         # بررسی اینکه آیا برای این DocID رکوردی وجود دارد یا نه
#         cursor.execute("""
#             SELECT COUNT(*)
#             FROM [LLMDB].[dbo].[LLM_Pipeline_Status]
#             WHERE DocID = ?
#         """, (_DocID,))

#         exists = cursor.fetchone()[0] > 0

#         if exists:
#             #بروزرسانی
#             query = """
#                 UPDATE [LLMDB].[dbo].[LLM_Pipeline_Status]
#                 SET 
#                     FileName = ?,
#                     Step = ?,
#                     Status = ?,
#                     ErrorMessage = ?,
#                     Timestamp = ?,
#                     ActionName = ?
#                 WHERE DocID = ?
#             """
#             params = (_FileName, _Step, _Status, _ErrorMessage, _Timestamp, _ActionName, _DocID)
            

#         else:
#             #درج جدید
#             query  = """
#                 INSERT INTO [LLMDB].[dbo].[LLM_Pipeline_Status]
#                     (DocID, FileName, Step, Status, ErrorMessage, Timestamp, ActionName)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             """
#             params = (_DocID, _FileName, _Step, _Status, _ErrorMessage, _Timestamp, _ActionName)
         
#         cursor.execute(query, params)
#         print("LogStatus saved successfully")

#     except Exception as e:
#         print(f"Error in LogStatus: {e}")
        
#         traceback.print_exc()
def LogStatus(_DocID, _ActionName, _FileName, _Step, _Status, _ErrorMessage, _Timestamp):
    try:
        print("S1:insert",flush=True)
        if _Timestamp is None:
            _Timestamp = datetime.now()

        with DatabaseConnection(connection_string) as cursor:
            print (connection_string)
            print(f"LogStatus => DocID={_DocID}, Action={_ActionName}, Step={_Step}, Status={_Status}")

            # اگر نام فایل پاس نشده، از جدول بخوان
            if not _FileName and _DocID != -1:
                print("S2:insert",flush=True)
                cursor.execute("""
                    SELECT Title
                    FROM [LLMDB].[dbo].[LLM_Documnts]
                    WHERE id = ?
                """, (_DocID,))
                row = cursor.fetchone()
                _FileName = row[0] if row else None

            # اگر باز هم FileName نداشتیم
            if not _FileName:
                print("S3:insert",flush=True)
                _FileName = "Unknown"

            # بررسی اینکه آیا برای این DocID رکوردی وجود دارد یا نه
            cursor.execute("""
                SELECT COUNT(*)
                FROM [LLMDB].[dbo].[LLM_Pipeline_Status]
                WHERE DocID = ? 
            """, (_DocID,))
            exists = cursor.fetchone()[0] > 0

            if exists and _DocID!=0:
                print("S4:insert",flush=True)
                print(_DocID)
                query = """
                    UPDATE [LLMDB].[dbo].[LLM_Pipeline_Status]
                    SET 
                        FileName = ?,
                        Step = ?,
                        Status = ?,
                        ErrorMessage = ?,
                        Timestamp = ?,
                        ActionName = ?
                    WHERE DocID = ?
                """
                params = (_FileName, _Step, _Status, _ErrorMessage, _Timestamp, _ActionName, _DocID)
            else:
                print("S5:insert",flush=True)
                print("insert",flush=True)
                query  = """
                    INSERT INTO [LLMDB].[dbo].[LLM_Pipeline_Status]
                        (DocID, FileName, Step, Status, ErrorMessage, Timestamp, ActionName)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                params = (_DocID, _FileName, _Step, _Status, _ErrorMessage, _Timestamp, _ActionName)
            
            cursor.execute(query, params)
            print("LogStatus saved successfully")

    except Exception as e:
        print(f"Error in LogStatus: {e}")
        traceback.print_exc()

def Deactivate_doc_from_sql(doc_id):
    try:
        with DatabaseConnection(connection_string) as cursor:
            query = """
            update [LLMDB].[dbo].[LLM_Documnts]  set isActive=0
            WHERE id = ?
            """
            cursor.execute(query, (doc_id,))
            deleted_rows = cursor.rowcount
        print(f" Document {doc_id} deactivated. Affected rows: {deleted_rows}")
    except Exception as e:
        print(f" Error deactivating document {doc_id}: {e}")
        
        traceback.print_exc()

def load_chunks_from_db():
   
    conn_str = connection_string
    
  
    query = """
    SELECT id, JsonData
    FROM dbo.LLM_Documnts
    WHERE IsActive = 1
    """

    chunks = []
    try:
        with DatabaseConnection(conn_str) as cursor:
    #with pyodbc.connect(conn_str) as conn:
      
        #cursor = conn.execute(query)
            cursor.execute(query)

            for row in cursor:
            
                table_id = row.id
                json_data = row.JsonData
            
                # اگر JSON به صورت string ذخیره شده
                data = json.loads(json_data)
           
                for chunk in data:
                    chunk_id = int(chunk["id"])

                    qdrant_id = int(f"{table_id}{chunk_id:05d}")
                    chunk["metadata"]["doc_id"] = str(table_id)
                    chunk["id"] = qdrant_id
                    chunks.append(chunk)
              
        return chunks
    except Exception as e:
        print(f"Error in load_chunks_from_db: {e}")
        traceback.print_exc()
        return []

def load_chunks_from_dbByDocId(docId):

    conn_str =connection_string

    query = f"""
        SELECT id, JsonData,
       replace(replace(LEFT(path, LEN(path) - CHARINDEX('/', REVERSE(path))),'data','media'),'/app/','')+'/img_folder'  AS folder_path
        FROM dbo.LLM_Documnts
        WHERE  id = ? 
        """
    #{docId}
    chunks = []
    table_id=0
    imagepath=''
    try:
        with DatabaseConnection(conn_str) as cursor:
    #with pyodbc.connect(conn_str) as conn:
        #cursor = conn.execute(query)
            cursor.execute(query, (docId,))
            data = []
            for row in cursor:
                table_id = row.id
                json_data = row.JsonData
                imagepath=row.folder_path
                # اگر JSON به صورت string ذخیره شده
                data = json.loads(json_data)

            for chunk in data:
                chunk_id = int(chunk["id"])

                qdrant_id = int(f"{table_id}{chunk_id:05d}")
                chunk["metadata"]["doc_id"] = str(table_id)
                chunk["id"] = qdrant_id
                chunks.append(chunk)
             
              
        return chunks,table_id,imagepath
    except Exception as e:
        print(f"Error in load_chunks_from_dbByDocId: {e}")
        traceback.print_exc()
        return [], table_id,imagepath
def SetIsActiveTrue(target_file_path, Doc_id): 
    file_name = os.path.basename(target_file_path)
    # conn = None
    # cursor = None
    try:
        # conn = pyodbc.connect(connection_string)
        # cursor = conn.cursor()
         with DatabaseConnection(connection_string) as cursor:
        # ۱. کوئری اصلاح شد: هم id و هم file_name اضافه شدند
        # ۲. مطمئن شوید نام ستون id است (اگر در دیتابیس اسمش Doc_id است، آن را تغییر دهید)
            cursor.execute("""
                UPDATE LLM_Documnts 
                SET IsActive = 1 
                WHERE Title = ? AND IsActive = 0 AND id = ?
            """, (file_name, Doc_id)) # حالا تعداد پارامترها با تعداد ? ها یکی است
        
        
            print(f" وضعیت {file_name} (ID: {Doc_id}) به فعال تغییر یافت.")
        
    except Exception as e:
        print(f" خطا در فعال‌سازی رکورد: {e}")
        traceback.print_exc()

def SetIsActiveFalse( Doc_id): 
    
    try:
        with DatabaseConnection(connection_string) as cursor:
        
        # ۱. کوئری اصلاح شد: هم id و هم file_name اضافه شدند
        # ۲. مطمئن شوید نام ستون id است (اگر در دیتابیس اسمش Doc_id است، آن را تغییر دهید)
            cursor.execute("""
                UPDATE LLM_Documnts 
                SET IsActive = 0 
                WHERE id = ? 
            """, ( Doc_id)) # حالا تعداد پارامترها با تعداد ? ها یکی است        
    except Exception as e:
        print(f"❌ خطا در غیرفعال‌سازی رکورد: {e}")
        traceback.print_exc()   
def InsertDocsToSql(target_file_path):
    file_name = os.path.basename(target_file_path)
    try:
        with DatabaseConnection(connection_string) as cursor:
        # ۱. خواندن محتوای فایل JSON
            with open(target_file_path, 'r', encoding='utf-8') as f:
                json_data = json.dumps(json.load(f), ensure_ascii=False)
                query_insert = """
                INSERT INTO LLM_Documnts (Title, Path, JsonData, IsActive)
                OUTPUT INSERTED.ID
                VALUES (?, ?, ?, 0)
            """
      
            cursor.execute(query_insert, (file_name, target_file_path, json_data))
            new_id = int(cursor.fetchone()[0])
            print(f"✅ رکورد جدید با موفقیت ثبت شد. ID جدید: {new_id}")
            return new_id

    except Exception as e:
        print(f"❌ خطا در درج دیتابیس رخ داد: {str(e)}")
        traceback.print_exc()
        return -1 
def SetALLRecord_IsActiveFalse( ): 
    
    try:
        with DatabaseConnection(connection_string) as cursor:
        
        # ۱. کوئری اصلاح شد: هم id و هم file_name اضافه شدند
        # ۲. مطمئن شوید نام ستون id است (اگر در دیتابیس اسمش Doc_id است، آن را تغییر دهید)
            cursor.execute("""
                UPDATE LLM_Documnts 
                SET IsActive = 0 
            
            """)
        
            print(" همه رکوردها با موفقیت غیرفعال شدند.")
    except Exception as e:
        print(f" خطا در غیرفعال‌سازی همه رکوردها: {e}")
        traceback.print_exc()
        
        
def bulk_charge_transactions(
    user_keys: List[str], 
    amount: int
    
    # admin_key: str
) -> dict:
    """
    ثبت گروهی تراکنش‌های شارژ کیف پول کاربران به صورت اتمیک در دیتابیس
    """
    query = """
        INSERT INTO [dbo].[WalletTransaction]
        ([UserKey], [Amount],  [CreatedTime], [TypeTransaction])
        VALUES (?, ?, ?, ?)
    """       
    current_time = datetime.now(timezone.utc) 
    inserted_count = 0 
    try:
        with DatabaseConnection(connection_string) as cursor:
            for user_key in user_keys:
                params = (user_key.strip(), amount,current_time,1)#شارژ
                cursor.execute(query,params)   
                inserted_count += 1
            
        # در صورت موفقیت، دیکشنری را برگردانید
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_amount": inserted_count * amount
        } 
    except Exception as e:
        print(f"خطا در عملیات: {e}")
        traceback.print_exc()
        raise