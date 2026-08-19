import mysql.connector
from mysql.connector import Error

# ===============================
# DATABASE CONFIG
# ===============================
DB_CONFIG = {
    'host': 'localhost',
    'database': 'cablevision_db',
    'user': 'root',
    'password': '',
    'port': 3306  # XAMPP default port (change ONLY if you really use 3307)
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
def execute_query(query, params=None, fetch=False, fetch_one=False):
    connection = get_db_connection()

    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, params or ())

        result = None

        if fetch:
            result = cursor.fetchall()

        elif fetch_one:
            result = cursor.fetchone()

        else:
            connection.commit()
            result = cursor.lastrowid

        return result

    except Error as e:
        print(f"[QUERY ERROR] {e}")
        return None

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
            print("[DB] Connection closed")