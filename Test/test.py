
import pyodbc

conn_str = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;DATABASE=LLMDB;UID=sa;PWD=Adonis123;TrustServerCertificate=yes;Encrypt=no;"

try:
    conn = pyodbc.connect(conn_str)
    print("اتصال موفقیت‌آمیز بود!")
    conn.close()
except Exception as e:
    print(f"خطای اتصال: {e}")
