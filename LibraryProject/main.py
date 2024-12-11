import os
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, Body, HTTPException, status, Response, Cookie
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader
from fastapi.openapi.utils import get_openapi

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
from bson.objectid import ObjectId

from contextlib import contextmanager
import json
from datetime import datetime

#enviroment for jinja2
file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)

username = quote_plus(os.getenv('MONGO_USERNAME'))
password = quote_plus(os.getenv('MONGO_PASSWORD'))
uri = os.getenv('MONGO_URI')
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

db = client['LibraryProject']

books_collection = db["Books"]
categories_collection = db["Categories"]
authors_collection = db["Authors"]
histories_collection = db["Histories"]
users_collection = db["Users"]

app = FastAPI(swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"})     #uvicorn main:app --reload


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Library API",
        version="2.2.9",
        summary="This is a very cool Library schema.",
        description="It has a rent function, post method's for all Tables, and Authorisation with Auntification.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": """https://static.vecteezy.com/system/
        resources/previews/004/852/937/large_2x/
        book-read-library-study-line-icon-illustration-logo-template-suitable-for-many-purposes-free-vector.jpg
        """
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi


@app.get("/", summary="Redirect to login page")
def main():
    """
    Redirect form empty page.
    """
    return RedirectResponse("/login")

def authenticate_user(email, password):
    # Access the Users collection
    users_collection = db['Users']
    # Find the user with the specified email
    searched_user = users_collection.find_one({"emailUser": email})

    # If the user is found and the password matches, return the user document
    if searched_user and searched_user.get("passwordUser") == password:
        return searched_user

    return None


@app.get("/login", summary="Login page")
def login_get(email: str | None = Cookie(default=None), password: str | None = Cookie(default=None)):
    """
    Retrieves the login page.
    """
    user = authenticate_user(email, password)
    if user:
        return RedirectResponse("/book-list")
    return FileResponse("templates/login.html")

    
@app.post("/login", summary="Post method for LogIn")
def login(data = Body()):
    """
    Handles the login request.
    """
    email = data.get("emailUser")
    password = data.get("passwordUser")
    searched_user = db['Users'].find_one({"emailUser": email})
    try:
        if searched_user['passwordUser'] == password:
            response = JSONResponse(content={"message": f"{searched_user}"})
            response.set_cookie(key="email", value=data.get("emailUser"))
            response.set_cookie(key="password", value=data.get("passwordUser"))
            return response
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")


@app.get("/registration", summary="Registration page")
def register_page():
    return FileResponse("templates/registration.html")


@app.post("/registration", summary="Post method for Registration")
def create_user(data = Body()):
    """
    Creates a new user with the provided data.
    """
    try:
        # Insert user data into the MongoDB collection
        inserted_user = users_collection.insert_one({
            "nameUser": data["nameUser"],
            "surnameUser": data["surnameUser"],
            "passwordUser": data["passwordUser"],
            "is_admin": False,
            "emailUser": data["emailUser"],
            "numberUser": data["numberUser"]
        })
        user = users_collection.find_one({"_id": inserted_user.inserted_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration failed")

    response = JSONResponse(content={"message": f"{user}"})
    response.set_cookie(key="email", value=data.get("emailUser"))
    response.set_cookie(key="password", value=data.get("passwordUser"))
    return response


@app.get("/categories")
async def get_categories():
    """
    Fetches all categories and returns them in a list.
    """
    try:
        categories = list(categories_collection.find({}, {"_id": 1, "nameCategory": 1}))
        return [
            {"_id": str(category["_id"]), "nameCategory": category["nameCategory"]}
            for category in categories
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/authors")
async def get_authors():
    """
    Fetches all authors and returns them in a list.
    """
    try:
        authors = list(authors_collection.find({}, {"_id": 1, "nameAuthor": 1, "surnameAuthor": 1}))
        return [
            {
                "_id": str(author["_id"]),
                "nameAuthor": author["nameAuthor"],
                "surnameAuthor": author["surnameAuthor"]
            }
            for author in authors
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@app.get("/book-list", summary="Books view in library")
def book_list_page(
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None)
):
    """
    Returns the book list page.
    """
    user = authenticate_user(email, password)
    if user:
        output = render_book_list(email, password)
        return HTMLResponse(output)
    else:
        return RedirectResponse("/login")
    

def render_book_list(email: str, password: str):
    """
    Returns the render of the book list page.
    """
    user = authenticate_user(email, password)
    if user["is_admin"]:
        template_file = 'book-list-roles/admin-book-list.html'
    else:
        template_file = 'book-list-roles/user-book-list.html'

    book_list_page = env.get_template(template_file)
    rents_book_id = []

    # Fetching books data
    books_dict = books_collection.aggregate([
        {
            "$lookup": {
                "from": "Categories",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category"
            }
        },
        {
            "$lookup": {
                "from": "Authors",
                "localField": "author_id",
                "foreignField": "_id",
                "as": "author"
            }
        },
        {
            "$unwind": "$author"  # Unwind the "author" array to separate the documents
        },
        {
            "$project": {
                "_id": 1,
                "nameBook": 1,
                "yearBook": 1,
                "availableBook": 1,
                "categoryName": "$category.nameCategory",
                "authorName": {"$concat": ["$author.nameAuthor", " ", "$author.surnameAuthor"]}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ])

    # Fetching rented books for non-admin users
    if not user["is_admin"]:
        rents = histories_collection.find({"user_id": user["_id"], "isReturned": False}, {"books_id": 1})
        rents_book_id = [rent["books_id"] for rent in rents]

    # Renders the book list page with appropriate data
    output = book_list_page.render(
        books=books_dict,
        username=email,
        rents_book_id=rents_book_id
    )
    
    return output

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


@app.get("/book/{book_id}", summary="Get for getting one specific book")
def book_page(book_id: str):
    """
    Retrieves information about a specific book by its ID.
    """
    try:
        # Fetch the book from the database
        book = books_collection.find_one({"_id": ObjectId(book_id)})
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Error accessing database: {e}")
        # Raise an HTTPException with a 500 status code
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error accessing database")

    if book is None:
        # If the book is not found, raise a 404 exception
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    # return {'message': 'Success'}
    return json.loads(json.dumps(book, cls=CustomJSONEncoder))


@app.post("/book", summary="Post method for Book")
def book_post_page(
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None),
    book_data=Body()
):
    """
    Adds a new book to the library.
    """
    user = authenticate_user(email, password)
    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    # Insert the book data into the Books collection
    result = books_collection.insert_one({
        "nameBook": book_data.get("nameBook"),
        "yearBook": book_data.get("yearBook"),
        "availableBook": book_data.get("availableBook"),
        "category_id": ObjectId(book_data.get("category_id")),
        "author_id": ObjectId(book_data.get("author_id"))
    })
    # Retrieve the inserted book from the collection
    inserted_book = books_collection.find_one({"_id": result.inserted_id})
    # Convert ObjectId to str for JSON serialization

    return {'message': 'Inserted successfully'}
        

@app.put("/book", summary="Put method for Book")
def edit_book(
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None),
    data = Body(),
):
    """
    Edits an existing book in the library.
    """
    user = authenticate_user(email, password)
    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    
    try:
        # Update the book data in the Books collection
        result = books_collection.update_one(
            {"_id": ObjectId(data.get("id"))},
            {"$set": {
                "nameBook": data.get("nameBook"),
                "yearBook": data.get("yearBook"),
                "availableBook": data.get("availableBook"),
                "category_id": ObjectId(data.get("category_id")),
                "author_id": ObjectId(data.get("author_id"))
            }}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book does not found")
        
        # Retrieve the updated book from the collection
        updated_book = books_collection.find_one({"_id": data.get("id")})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating book in the database")

    return {'message': 'Updated successfully'}

@app.delete("/book/{book_id}", summary="Delete method for Book")
def delete_book(book_id: str, email: str | None = Cookie(default=None), password: str | None = Cookie(default=None)):
    """
    Deletes a book from the library based on its ID.
    """
    user = authenticate_user(email, password)
    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")

    try:
        # Convert the book_id to ObjectId
        book_id_obj = ObjectId(book_id)
        
        # Delete the book from the Books collection
        deleted_book = books_collection.find_one_and_delete({"_id": book_id_obj})
        
        if deleted_book:
            return {'message': 'Deleted successfully'}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting book from the database")


@app.post("/book/{book_id}/rent", summary="Renting a book")
def rent_book(
    book_id: str,
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None)
):
    """
    Rent a book for a user.
    """
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    try:
        # Converts the book_id to ObjectId
        book_id_obj = ObjectId(book_id)
        
        # Checks if there's an existing rental record
        rent = histories_collection.find_one({"user_id": user['_id'], "books_id": book_id_obj, "isReturned": False})
        if rent:  # If rental record already exists
            # Updates existing rental record
            histories_collection.update_one(
                {"_id": rent["_id"]},
                {"$set": {"isReturned": True, "dateReturn": date_now}}
            )
            # Increases the availableBook count in the Books collection
            books_collection.update_one({"_id": book_id_obj}, {"$inc": {"availableBook": 1}})
        else:  # Else creates a new rental record
            # Inserts new rental record
            histories_collection.insert_one({
                "user_id": user['_id'],
                "books_id": book_id_obj,
                "dateLoan": date_now,
                "isReturned": False
            })
            # Decreases the availableBook count in the Books collection
            books_collection.update_one({"_id": book_id_obj}, {"$inc": {"availableBook": -1}})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    return {"message": "Book rented successfully."}

@app.get("/rents-list", summary="List of Rents")
def book_list_page(
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None)
):
    user = authenticate_user(email, password)
    if user:
        if user["is_admin"]:
            output = render_rent_list(user)
            return HTMLResponse(output)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    else:
        return RedirectResponse("/login")

def render_rent_list(user):
    """
    Renders the rent list with additional data for usernames and book names.
    """
    book_list_page = env.get_template('rent-list.html')

    # Aggregating rental data with user and book information
    rents = histories_collection.aggregate([
        {
            "$lookup": {
                "from": "Users",  # The name of the Users collection
                "localField": "user_id",  # Field in Histories to match
                "foreignField": "_id",  # Field in Users to match
                "as": "user"  # Output array field for joined data
            }
        },
        {
            "$lookup": {
                "from": "Books",  # The name of the Books collection
                "localField": "books_id",  # Field in Histories to match
                "foreignField": "_id",  # Field in Books to match
                "as": "book"  # Output array field for joined data
            }
        },
        {
            "$unwind": "$user"  # Flatten the user array
        },
        {
            "$unwind": "$book"  # Flatten the book array
        },
        {
            "$project": {
                "_id": 1,
                "user_id": 1,
                "books_id": 1,
                "dateLoan": 1,
                "dateReturn": 1,
                "isReturned": 1,
                "username": "$user.emailUser",  # Replace with the correct username field in Users
                "bookName": "$book.nameBook"  # Replace with the correct book name field in Books
            }
        },
        {
            "$sort": {"isReturned": 1, "dateLoan": -1}
        }
    ])

    rents_list = list(rents)  # Convert the cursor to a list

    output = book_list_page.render(
        rents=rents_list,
        username=user['emailUser']  # Pass the current user's email
    )
    return output


@app.post("/authors", summary="Post method for Authors")
def authors_post_page(data: list[dict] = Body(...)):
    """
    Create new authors with the provided data.
    """
    try:
        for author_data in data:
            # Insert each author into the Authors collection
            authors_collection.insert_one(author_data)
        # Fetch all authors after insertion
        authors = authors_collection.find()
        authors_dict = [author for author in authors]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return authors_dict

@app.post("/categories", summary="Post method for Categories")
def categories_post_page(data: list[dict] = Body(...)):
    """
    Create new categories with the provided data.
    """
    try:
        for category_data in data:
            # Insert each category into the Categories collection
            categories_collection.insert_one(category_data)
        # Fetch all categories after insertion
        categories = categories_collection.find()
        categories_dict = [category for category in categories]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return categories_dict

@app.post("/book-list", summary="Post method for Books")
def books_post_page(data: list[dict] = Body(...)):
    """
    Create new books with the provided data.
    """
    try:
        for book_data in data:
            # Insert each book into the Books collection
            books_collection.insert_one(book_data)
        # Fetch all books after insertion
        books = books_collection.find()
        books_dict = [book for book in books]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return books_dict


@app.get("/clear-cookie", summary="Clearing Cookies")
def clear_cookie(response: Response):
    response.delete_cookie("email")
    response.delete_cookie("password")
    return {"message": "Cookie cleared successfully"}