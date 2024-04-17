from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
from bson.objectid import ObjectId


username = quote_plus('reyget')
password = quote_plus('xPCTVF6:3u,b=qn')
uri = "mongodb+srv://" + username + ":" + password+"@pythonweb.mbdiw74.mongodb.net/?retryWrites=true&w=majority&appName=PythonWEB"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client['LibraryProject']

authors_collection = db['Authors']
categories_collection = db['Categories']
books_collection = db['Books']
users_collection = db['Users']
histories_collection = db['Histories']

def authenticate_user(email, password):
    # Access the Users collection
    users_collection = db['Users']
    # Find the user with the specified email
    searched_user = users_collection.find_one({"emailUser": email})

    # If the user is found and the password matches, return the user document
    if searched_user and searched_user.get("passwordUser") == password:
        return searched_user

    return None


email = 'Admin@gmail.com'
password = 'password'

def test():
    # user = authenticate_user(email, password)
    # if user["is_admin"]:
    #     template_file = 'book-list-roles/admin-book-list.html'
    # else:
    #     template_file = 'book-list-roles/user-book-list.html'

    # # Fetching books data
    # books_dict = books_collection.aggregate([
    #     {
    #         "$lookup": {
    #             "from": "Categories",
    #             "localField": "category_id",
    #             "foreignField": "_id",
    #             "as": "category"
    #         }
    #     },
    #     {
    #         "$lookup": {
    #             "from": "Authors",
    #             "localField": "author_id",
    #             "foreignField": "_id",
    #             "as": "author"
    #         }
    #     },
    #     {
    #         "$unwind": "$author"  # Unwind the "author" array to separate the documents
    #     },
    #     {
    #         "$project": {
    #             "_id": 1,
    #             "nameBook": 1,
    #             "yearBook": 1,
    #             "availableBook": 1,
    #             "categoryName": "$category.nameCategory",
    #             "authorName": {"$concat": ["$author.nameAuthor", " ", "$author.surnameAuthor"]}
    #         }
    #     },
    #     {
    #         "$sort": {"_id": 1}
    #     }
    # ])
    # print([book['categoryName'] for book in books_dict])
    book_id = '6620023de5a4249451ed7754'

    book = books_collection.find_one({"_id": ObjectId(book_id)})

    print(book)

test()