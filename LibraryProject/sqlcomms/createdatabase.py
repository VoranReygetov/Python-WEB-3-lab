import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    host="127.0.0.1",
    user="postgres",
    password="password",
    port="5432"
)

conn.autocommit = True
cursor = conn.cursor()
sql = "CREATE DATABASE LibraryProject"
cursor.execute(sql)
print("База даних успішно створена")

cursor.close()
conn.close()