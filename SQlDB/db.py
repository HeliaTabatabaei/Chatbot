import pyodbc
class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self.cursor = None

    def __enter__(self):
        print('1111111111111111111111111111')
        self.conn = pyodbc.connect(self.connection_string)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()
        self.conn.close()
