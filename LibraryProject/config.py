# config.py
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

username = os.getenv('MONGO_USERNAME')
password = os.getenv('MONGO_PASSWORD')
uri = os.getenv('MONGO_URI')
