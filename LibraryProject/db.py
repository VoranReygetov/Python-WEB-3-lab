# db.py
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus

# MongoDB client setup
username = quote_plus(os.getenv('MONGO_USERNAME'))
password = quote_plus(os.getenv('MONGO_PASSWORD'))
uri = os.getenv('MONGO_URI')

client = MongoClient(uri, server_api=ServerApi('1'))

# Database selection
db = client['LibraryProject']

# Collections
books_collection = db["Books"]
categories_collection = db["Categories"]
authors_collection = db["Authors"]
histories_collection = db["Histories"]
users_collection = db["Users"]
