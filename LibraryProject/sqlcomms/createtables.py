import psycopg2

# Connect to the database
conn = psycopg2.connect(
    dbname="libraryproject",
    host="127.0.0.1",
    user="postgres",
    password="password",
    port="5432"
)

# Create a cursor object
cur = conn.cursor()

# Create tables
cur.execute('''
    CREATE TABLE Genres (
        id SERIAL PRIMARY KEY,
        genre_id INTEGER REFERENCES Users(id) NOT NULL,
        genre_name VARCHAR 
    )
''')

cur.execute('''
    CREATE TABLE Authors (
        id SERIAL PRIMARY KEY,
        nameAuthor VARCHAR,
        surnameAuthor VARCHAR
    )
''')

cur.execute('''
    CREATE TABLE Categories (
        id SERIAL PRIMARY KEY,
        nameCategory VARCHAR NOT NULL
    )
''')

cur.execute('''
    CREATE TABLE Books (
        id SERIAL PRIMARY KEY,
        nameBook VARCHAR NOT NULL,
        yearBook INTEGER,
        availableBook INTEGER,
        category_id INTEGER REFERENCES Categories(id),
        author_id INTEGER REFERENCES Authors(id)
    )
''')

cur.execute('''
    CREATE TABLE Users (
        id SERIAL PRIMARY KEY,
        nameUser VARCHAR NOT NULL,
        surnameUser VARCHAR,
        passwordUser VARCHAR NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        emailUser VARCHAR UNIQUE NOT NULL,
        numberUser INTEGER
    )
''')

cur.execute('''
    CREATE TABLE Histories (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES Users(id) NOT NULL,
        books_id INTEGER REFERENCES Books(id) NOT NULL,
        dateLoan TIMESTAMP(0) NOT NULL,
        dateReturn TIMESTAMP(0),
        isReturned BOOLEAN DEFAULT FALSE
    )
''')


print("Таблиці успішно створені")
# Commit the transaction
conn.commit()

# Close the cursor and connection
cur.close()
conn.close()
