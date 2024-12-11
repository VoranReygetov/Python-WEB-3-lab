# routes.py
import os
import bcrypt
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Body, Request, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from bson.objectid import ObjectId
from db import books_collection, categories_collection, authors_collection, histories_collection, users_collection
from auth import authenticate_user
from jinja2 import Environment, FileSystemLoader
from auth import authenticate_user, create_access_token, verify_token

from db import db
from config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

# Jinja2 template setup
file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)

# Routes - Authentication and User Management

@router.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('favicon.ico')

@router.get("/login", summary="Login page")
def login_get(request: Request):
    """
    Render the login page. If the user is already authenticated, redirect them to the book list.
    """
    token = request.cookies.get("access_token")
    if token:
        try:
            user_data = verify_token(token)
            user = db['Users'].find_one({"emailUser": user_data["sub"]})
            if user:
                return RedirectResponse("/book-list")
        except Exception:
            pass  # Invalid or expired token
    return FileResponse("templates/login.html")

@router.post("/login", summary="Login to obtain JWT token")
def login(data=Body()):
    """
    Login user by verifying credentials and providing an access token.
    """
    email = data.get("emailUser")
    password = data.get("passwordUser")
    searched_user = db['Users'].find_one({"emailUser": email})

    if not searched_user or not bcrypt.checkpw(password.encode('utf-8'), searched_user['passwordUser'].encode('utf-8')):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")

    token = create_access_token({"sub": searched_user['emailUser']}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
    return response

@router.get("/registration", summary="Registration page")
def register_page():
    """
    Render the registration page.
    """
    return FileResponse("templates/registration.html")

@router.post("/registration", summary="Post method for Registration")
def create_user(data=Body()):
    """
    Create a new user with the provided data, hashing the password, and assigning a creation date.
    """
    try:
        # Hash the password
        hashed_password = bcrypt.hashpw(data["passwordUser"].encode('utf-8'), bcrypt.gensalt())

        # Add the creation date
        creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert user data into the database
        inserted_user = users_collection.insert_one({
            "nameUser": data["nameUser"],
            "surnameUser": data["surnameUser"],
            "passwordUser": hashed_password.decode('utf-8'),
            "is_admin": False,
            "emailUser": data["emailUser"],
            "numberUser": data["numberUser"],
            "created_at": creation_date
        })

        user = users_collection.find_one({"_id": inserted_user.inserted_id})

    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration failed")

    response = JSONResponse(content={"message": f"User {user['nameUser']} successfully registered"})
    token = create_access_token({"sub": user['emailUser']}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True)

    return response

@router.get("/clear-cookie", summary="Clear the authentication cookie")
def clear_cookie():
    """
    Clears the authentication cookie.
    """
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response

# Routes - Book and Category Management

@router.get("/book-list", summary="Books view in library")
def book_list_page(request: Request):
    """
    Displays a list of books, with data tailored based on the user's role (admin/user).
    """
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})
    output = render_book_list(user)
    return HTMLResponse(output)

def render_book_list(user):
    """
    Renders the list of books, differentiating between admin and user roles.
    """
    if user["is_admin"]:
        template_file = 'book-list-roles/admin-book-list.html'
    else:
        template_file = 'book-list-roles/user-book-list.html'

    book_list_page = env.get_template(template_file)
    rents_book_id = []

    books_dict = books_collection.aggregate([
        {"$lookup": {"from": "Categories", "localField": "category_id", "foreignField": "_id", "as": "category"}},
        {"$lookup": {"from": "Authors", "localField": "author_id", "foreignField": "_id", "as": "author"}},
        {"$unwind": "$author"},
        {"$project": {
            "_id": 1, "nameBook": 1, "yearBook": 1, "availableBook": 1,
            "categoryName": "$category.nameCategory",
            "authorName": {"$concat": ["$author.nameAuthor", " ", "$author.surnameAuthor"]}
        }},
        {"$sort": {"_id": 1}}
    ])

    if not user["is_admin"]:
        rents = histories_collection.find({"user_id": user["_id"], "isReturned": False}, {"book_id": 1})
        rents_book_id = [rent["book_id"] for rent in rents]

    output = book_list_page.render(
        books=books_dict,
        username=user["emailUser"],
        rents_book_id=rents_book_id
    )
    return output

@router.post("/book", summary="Post method for Book")
def book_post_page(request: Request, data = Body()):
    """
    Adds a new book to the library.
    Only accessible to admin users.
    """
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    
    books_collection.insert_one({
        "nameBook": data.get("nameBook"),
        "yearBook": data.get("yearBook"),
        "availableBook": data.get("availableBook"),
        "category_id": ObjectId(data.get("category_id")),
        "author_id": ObjectId(data.get("author_id"))
    })

    return {"message": "Book added successfully."}

@router.put("/book", summary="Put method for Book")
def edit_book(request: Request, data = Body()):
    """
    Edits an existing book in the library. 
    Only accessible to admin users.
    """
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    return {'message': 'Updated successfully'}

@router.delete("/book/{book_id}", summary="Delete method for Book")
def delete_book(book_id: str, request: Request):
    """
    Deletes a book from the library based on its ID.
    Only accessible to admin users.
    """
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")

    book_id_obj = ObjectId(book_id)
    deleted_book = books_collection.find_one_and_delete({"_id": book_id_obj})

    if deleted_book:
        return {'message': 'Deleted successfully'}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

@router.post("/book-list", summary="Post method for Books")
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

# Routes - Renting and History Management

@router.post("/book/{book_id}/rent", summary="Renting a book")
def rent_book(book_id: str, request: Request):
    """
    Rent or return a book for a user.
    """
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    book = books_collection.find_one({"_id": ObjectId(book_id)})

    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    rented_book = histories_collection.find_one({"book_id": ObjectId(book_id), "user_id": user["_id"], "isReturned": False})

    if rented_book:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book already rented")
    
    histories_collection.insert_one({
        "book_id": ObjectId(book_id),
        "user_id": user["_id"],
        "rent_date": date_now,
        "isReturned": False
    })

    return {"message": "Book rented successfully."}

@router.get("/rents-list", summary="List of Rents")
def book_list_page(request: Request):

    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    if user and user.get("is_admin"):
        output = render_rent_list(user)
        return HTMLResponse(output)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")


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
                "localField": "book_id",  # Field in Histories to match
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
                "book_id": 1,
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

# Routes - Categories and Authors Management

@router.get("/categories")
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
    
@router.get("/authors")
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
    
@router.post("/authors", summary="Post method for Authors")
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

@router.post("/categories", summary="Post method for Categories")
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