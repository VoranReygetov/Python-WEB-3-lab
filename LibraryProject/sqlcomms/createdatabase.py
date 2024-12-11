from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus

username = quote_plus('reyget')
password = quote_plus('cWX3f3hyzh2XOQf2')
uri = "mongodb+srv://" + username + ":" + password + "@libraryproject.2tink.mongodb.net/?retryWrites=true&w=majority&appName=LibraryProject"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    db = client['LibraryProject']
    print(db.name)
    print("База даних "+db.name+" успішно створена")

    authors_collection = db['Authors']
    categories_collection = db['Categories']
    books_collection = db['Books']
    users_collection = db['Users']
    histories_collection = db['Histories']

    print("Документи даних "+authors_collection.name, categories_collection.name, books_collection.name, users_collection.name, histories_collection.name+" успішно створені")
    # Define data
    users_collection.create_index("emailUser", unique=True)
    categories_collection.create_index("nameCategory", unique=True)

    authors_data = [{"nameAuthor": "George", "surnameAuthor": "Orwell"},
                    {"nameAuthor": "J.K.", "surnameAuthor": "Rowling"},
                    {"nameAuthor": "Stephen", "surnameAuthor": "King"},
                    {"nameAuthor": "Jane", "surnameAuthor": "Austen"}]

    categories_data = [{"nameCategory": "Child"},
                    {"nameCategory": "Adults"},
                    {"nameCategory": "Horror"},
                    {"nameCategory": "Classic"}]

    users_data = [{"nameUser": "Admin", "surnameUser": "Admin", "passwordUser": "password", "is_admin": True, "emailUser": "Admin@gmail.com"}]

    # Insert data into collections
    authors_result = authors_collection.insert_many(authors_data)
    categories_result = categories_collection.insert_many(categories_data)
    users_result = users_collection.insert_many(users_data)

    books_data = [{"nameBook": "The Shining", "yearBook": 1977, "availableBook": 3, "category_id": categories_result.inserted_ids[2], "author_id": authors_result.inserted_ids[0]},
                {"nameBook": "Harry Potter", "yearBook": 1997, "availableBook": 7, "category_id": categories_result.inserted_ids[3], "author_id": authors_result.inserted_ids[1]},
                {"nameBook": "Disappearance", "yearBook": 1998, "availableBook": 2, "category_id": categories_result.inserted_ids[2], "author_id": authors_result.inserted_ids[2]},
                {"nameBook": "Pride and Prejudice", "yearBook": 1813, "availableBook": 12, "category_id": categories_result.inserted_ids[1], "author_id": authors_result.inserted_ids[3]},
                {"nameBook": "Another Book", "yearBook": 2000, "availableBook": 4, "category_id": categories_result.inserted_ids[0], "author_id": authors_result.inserted_ids[1]}]


    books_result = books_collection.insert_many(books_data)
    # Print acknowledgment
    print("Введені автори:", [r for r in authors_collection.find()])
    print("Введені категорії:", [r for r in categories_collection.find()])
    print("Введені книжки:", [r for r in books_collection.find()])
    print("Введені користувачі:", [r for r in users_collection.find()])
except Exception as e:
    print(e)