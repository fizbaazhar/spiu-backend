import pyodbc
from .config import Config


def get_sql_connection():
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={Config.SQL_SERVER};'
        f'DATABASE={Config.SQL_DATABASE};'
        f'UID={Config.SQL_USERNAME};'
        f'PWD={Config.SQL_PASSWORD};'
        f'Trusted_Connection=no;'
    )
