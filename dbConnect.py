import pyodbc
import os

# Retrieve database configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost\\MSSQLSERVER")
DB_PORT = os.getenv("DB_PORT", "1558")
DB_USER = os.getenv("DB_USER", "APIS_TEST")
DB_PASSWORD = os.getenv("DB_PASSWORD", "apis@2025")
DB_NAME = os.getenv("DB_NAME", "TaxAPI")

# Connection string
conn_str = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={DB_HOST},{DB_PORT};'
    f'DATABASE={DB_NAME};'
    f'UID={DB_USER};'
    f'PWD={DB_PASSWORD};'
)

try:
    # Establish connection
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")  # Simple test query
    result = cursor.fetchone()
    if result:
        print("Database connection successful!")
    else:
        print("Connected, but test query failed!")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Database connection failed: {e}")
