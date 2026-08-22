import os
import mysql.connector
from mysql.connector import Error

# ===============================
# DATABASE CONFIG
# ===============================
DB_CONFIG = {
    'host': os.getenv('MYSQLHOST', 'localhost'),
    'database': os.getenv('MYSQLDATABASE', 'cablevision_db'),
    'user': os.getenv('MYSQLUSER', 'root'),
    'password': os.getenv('MYSQLPASSWORD', ''),
    'port': int(os.getenv('MYSQLPORT', 3306))
}

# ===============================
# CONNECTION
# ===============================
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            print("[DB] Connected successfully")
            return connection

    except Error as e:
        print(f"[DB CONNECTION ERROR] {e}")

    return None


# ===============================
# UNIVERSAL QUERY EXECUTOR
# ===============================
def execute_query(query, params=None, fetch=False, fetch_one=False, fetch_all=False):
    connection = get_db_connection()

    if not connection:
        print("[DB] Connection failed")
        return None

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        print(f"[QUERY] {query}")
        print(f"[PARAMS] {params}")

        if isinstance(params, list):
            params = tuple(params)

        cursor.execute(query, params or ())

        result = None

        # Fetch multiple rows
        if fetch or fetch_all:
            result = cursor.fetchall()

        # Fetch single row
        elif fetch_one:
            result = cursor.fetchone()

        # INSERT / UPDATE / DELETE
        else:
            connection.commit()
            result = cursor.lastrowid

        return result

    except Error as e:
        print(f"[QUERY ERROR] {e}")

        if connection:
            connection.rollback()

        return None

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
            print("[DB] Connection closed")