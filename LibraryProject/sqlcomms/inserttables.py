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

#inserts into tables
Authors = [("George","Orwell"),("J.K.","J.K. Rowling"),("Stephen","King"),("Jane","Austen")]
cur.executemany("INSERT INTO Authors(nameAuthor, surnameAuthor) VALUES(%s, %s)", Authors)

Categories = [("Child",), ("Adults",), ("Horror",), ("Classic",)]
cur.executemany("INSERT INTO Categories(nameCategory) VALUES(%s)", Categories)

# Commit the transaction
conn.commit()
print("Додано батьківські елементи")

Books = [("The Shining",1977,3,5,9),("Harry Potter",1997, 7,6,10),("Disappearance", 1998,2,7,11),("Pride and Prejudice", 1813, 12,8,12), ("Another Book", 2000, 4, 5, 10)]
cur.executemany("INSERT INTO Books(nameBook, yearBook, availableBook, category_id, author_id) VALUES(%s, %s, %s, %s, %s)", Books)

Users = [("Admin", "Admin", "password",  True, "Admin@gmail.com")]
cur.executemany("INSERT INTO Users(nameUser, surnameUser, passwordUser,is_admin,emailUser) VALUES(%s, %s, %s, %s, %s)", Users)

conn.commit()

print("Додано дитячі елементи з референсом")
# Close the cursor and connection
cur.close()
conn.close()


