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
            # ✅ I-SET ANG SESSION TIMEZONE SA PHILIPPINE TIME
            # Para tama ang lahat ng CURRENT_TIMESTAMP, NOW(), at DEFAULT timestamps
            cursor = connection.cursor()
            cursor.execute("SET time_zone = '+08:00'")
            cursor.close()
            
            print("[DB] Connected successfully (timezone set to +08:00)")
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

        # ===============================
        # FETCH MULTIPLE ROWS
        # ===============================
        if fetch or fetch_all:
            result = cursor.fetchall()

        # ===============================
        # FETCH ONE ROW
        # ===============================
        elif fetch_one:
            result = cursor.fetchone()

        # ===============================
        # INSERT / UPDATE / DELETE
        # ===============================
        else:
            connection.commit()

            # IMPORTANT:
            # Use rowcount instead of lastrowid
            result = cursor.rowcount

            print(f"[AFFECTED] {result} rows affected")

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