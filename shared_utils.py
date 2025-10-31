from flask import request, jsonify
import pyodbc
import os
import hashlib

# --- Authentication ---
stored_token = os.getenv("API_TOKEN")

def token_required(f):
    """Decorator to protect routes with Bearer Token Authentication."""
    def wrapper(*args, **kwargs):
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        
        # Check if the Authorization header is provided and in the correct format
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"msg": "Missing or invalid Authorization header"}), 401
        
        # Extract the token
        token = auth_header.split(" ")[1]
        
        # Compare the provided token with the stored token
        if token != stored_token:
            return jsonify({"msg": "Invalid token"}), 401
        
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__  # Preserve the name of the original function
    return wrapper


# Retrieve database configuration from environment variables
# production server
# DB_HOST = os.getenv("DB_HOST", "localhost\\MSSQLSERVER")
# DB_PORT = os.getenv("DB_PORT", "14661")
# DB_USER = os.getenv("DB_USER", "taxapi")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "apis@2024.com")
# DB_NAME = os.getenv("DB_NAME", "TaxAPI")

# test_server 202.137.147.5
DB_HOST = os.getenv("DB_HOST", "localhost\\MSSQLSERVER")
DB_PORT = os.getenv("DB_PORT", "1558")
DB_USER = os.getenv("DB_USER", "APIS_TEST")
DB_PASSWORD = os.getenv("DB_PASSWORD", "apis@2025")
DB_NAME = os.getenv("DB_NAME", "TaxAPI")

def get_db_connection():
    """Establish a connection to the MSSQL database."""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_HOST},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD}"
    )
    return pyodbc.connect(connection_string)

# --- Signature and Other Helpers ---
def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def generate_signature(key_code, sign_date, order_no):
    """Generate a signature using keyCode, signDate, and ORDER_NO."""
    concatenated = f"{key_code}{sign_date}{order_no}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

def generate_signature_apis(key_code, sign_date):
    """Generate a signature using keyCode, signDate"""
    concatenated = f"{key_code}{sign_date}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

def clean_string(value):
    """
    Strips leading/trailing whitespace from a string.
    Returns the original value if it's not a string (e.g., None, int, float).
    """
    if isinstance(value, str):
        return value.strip()
    return value