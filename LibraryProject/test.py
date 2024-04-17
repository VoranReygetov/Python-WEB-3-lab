import psycopg2
from contextlib import contextmanager
import json
@contextmanager
def connection_pstgr():
    conn = psycopg2.connect(
        dbname="libraryproject",
        host="127.0.0.1",
        user="postgres",
        password="password",
        port="5432"
    )
    cursor = conn.cursor()
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

def authenticate_user(email: str, password: str):
    """
    Checking in Users table by passed emails to LogIn form.
    """
    with connection_pstgr() as (conn, cursor):
        cursor.execute("SELECT * FROM Users WHERE emailUser = %s", (email,))
        searched_user = cursor.fetchone()
        if searched_user and searched_user[3] == password:
            columns = [desc[0] for desc in cursor.description]
            user_dict = dict(zip(columns, searched_user))
            return user_dict
        else:
            return None
        
# with connection_pstgr() as (conn, cursor):
    # cursor.execute("SELECT * FROM Users")
    # searched_user = cursor.fetchone()
    # columns = [desc[0] for desc in cursor.description]
    # print(searched_user[0])
    # book_dict = dict(zip(columns, searched_user))
    # inserted_book_json = json.dumps(book_dict)\
with connection_pstgr() as (conn, cursor): 
   user = authenticate_user("Admin@gmail.com", "password")

print(user)
# Now the connection and cursor are automatically closed after exiting the with block
