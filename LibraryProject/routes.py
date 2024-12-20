# routes.py
import os
import bcrypt
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Body, Depends, Request, status, Form
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from bson.objectid import ObjectId
from db import books_collection, categories_collection, authors_collection, histories_collection, users_collection
from auth import authenticate_user
from jinja2 import Environment, FileSystemLoader
from auth import authenticate_user, create_access_token, verify_token
from typing import List, Dict

from models import LoginRequest, RegistrationRequest, BookRequest, Category, Author
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
def login(data: LoginRequest):
    """
    Login user by verifying credentials and providing an access token.
    """
    email = data.emailUser
    password = data.passwordUser
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
def create_user(data: RegistrationRequest):
    """
    Create a new user with the provided data, hashing the password, and assigning a creation date.
    """
    try:
        # Hash the password
        hashed_password = bcrypt.hashpw(data.passwordUser.encode('utf-8'), bcrypt.gensalt())

        # Add the creation date
        creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert user data into the database
        inserted_user = users_collection.insert_one({
            "nameUser": data.nameUser,
            "surnameUser": data.surnameUser,
            "passwordUser": hashed_password.decode('utf-8'),
            "is_admin": False,
            "emailUser": data.emailUser,
            "numberUser": data.numberUser,
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
def book_post_page(request: Request, data: BookRequest):
    """
    Adds a new book to the library.
    Only accessible to admin users.
    """
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    
    books_collection.insert_one({
        "nameBook": data.nameBook,
        "yearBook": data.yearBook,
        "availableBook": data.availableBook,
        "category_id": ObjectId(data.category_id),
        "author_id": ObjectId(data.author_id)
    })

    return {"message": "Book added successfully."}

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)  # Convert ObjectId to string
        return super().default(obj)
    
@router.get("/book/{book_id}", summary="Get for getting one specific book")
def book_page(book_id: str):
    """
    Retrieves information about a specific book by its ID.
    """
    # Fetch the book from the database
    book = books_collection.find_one({"_id": ObjectId(book_id)})

    if not book:
        # If the book is not found, raise a 404 exception
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    # Return the book as a JSON response
    return JSONResponse(content=json.loads(json.dumps(book, cls=CustomJSONEncoder)))

@router.put("/book", summary="Put method for Book")
def edit_book(request: Request, data: BookRequest):
    """
    Edits an existing book in the library. 
    Only accessible to admin users.
    """
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})

    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    
    result = books_collection.update_one(
        {"_id": ObjectId(data.id)},  
        {"$set": {
            "nameBook": data.nameBook,
            "yearBook": data.yearBook,
            "availableBook": data.availableBook,
            "category_id": ObjectId(data.category_id),
            "author_id": ObjectId(data.author_id)
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
    # Authenticate user
    user_data = authenticate_user(request)
    user = db['Users'].find_one({"emailUser": user_data["sub"]})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")
    try:
        # Convert the book_id to ObjectId
        book_id_obj = ObjectId(book_id)
        # Check if there's an existing rental record
        rent = histories_collection.find_one({"user_id": user['_id'], "book_id": book_id_obj, "isReturned": False})
        if rent:  # If rental record already exists (returning the book)
            # Update the existing rental record
            histories_collection.update_one(
                {"_id": rent["_id"]},
                {"$set": {"isReturned": True, "dateReturn": date_now}}
            )
            # Increase the availableBook count in the Books collection
            books_collection.update_one({"_id": book_id_obj}, {"$inc": {"availableBook": 1}})
            # Fetch updated availableBook count
            updated_book = books_collection.find_one({"_id": book_id_obj})
            available_books = updated_book["availableBook"]
            return {"message": "Book returned successfully.", "availableBook": available_books}
        else:  # Else create a new rental record (renting the book)
            # Insert a new rental record
            histories_collection.insert_one({
                "user_id": user['_id'],
                "book_id": book_id_obj,
                "dateLoan": date_now,
                "isReturned": False
            })
            # Decrease the availableBook count in the Books collection
            books_collection.update_one({"_id": book_id_obj}, {"$inc": {"availableBook": -1}})
            # Fetch updated availableBook count
            updated_book = books_collection.find_one({"_id": book_id_obj})
            available_books = updated_book["availableBook"]
            return {"message": "Book rented successfully.", "availableBook": available_books}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.get("/rents-list", summary="List of Rents")
def book_list_page(request: Request):
    """
    Renders the rent list page for the current user.
    Admins see all rents, while regular users see only their rents.
    """
    user_data = authenticate_user(request)
    user = db["Users"].find_one({"emailUser": user_data["sub"]})

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.get("is_admin"):
        # Admins see all rents
        output = render_rent_list(user)
    else:
        # Regular users see only their rents
        output = render_user_rent_list(user)

    return HTMLResponse(output)


def render_rent_list(user):
    """
    Renders the rent list with all rents for admin users.
    """
    book_list_page = env.get_template("rent-list.html")

    # Aggregating rental data with user and book information
    rents = histories_collection.aggregate([
        {
            "$lookup": {
                "from": "Users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {
            "$lookup": {
                "from": "Books",
                "localField": "book_id",
                "foreignField": "_id",
                "as": "book",
            }
        },
        {"$unwind": "$user"},
        {"$unwind": "$book"},
        {
            "$project": {
                "_id": 1,
                "user_id": 1,
                "book_id": 1,
                "dateLoan": 1,
                "dateReturn": 1,
                "isReturned": 1,
                "username": "$user.emailUser",
                "bookName": "$book.nameBook",
            }
        },
        {"$sort": {"isReturned": 1, "dateLoan": -1}},
    ])

    rents_list = list(rents)

    output = book_list_page.render(
        rents=rents_list,
        username=user["emailUser"]
    )
    return output


def render_user_rent_list(user):
    """
    Renders the rent list for a regular user, showing only their rents.
    """
    book_list_page = env.get_template("rent-list.html")

    # Aggregating rental data for the current user
    rents = histories_collection.aggregate([
        {"$match": {"user_id": user["_id"]}},
        {
            "$lookup": {
                "from": "Users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {
            "$lookup": {
                "from": "Books",
                "localField": "book_id",
                "foreignField": "_id",
                "as": "book",
            }
        },
        {"$unwind": "$user"},
        {"$unwind": "$book"},
        {
            "$project": {
                "_id": 1,
                "user_id": 1,
                "book_id": 1,
                "dateLoan": 1,
                "dateReturn": 1,
                "isReturned": 1,
                "username": "$user.emailUser",
                "bookName": "$book.nameBook",
            }
        },
        {"$sort": {"isReturned": 1, "dateLoan": -1}},
    ])

    rents_list = list(rents)

    output = book_list_page.render(
        rents=rents_list,
        username=user["emailUser"]
    )
    return output

    
# Routes - JWT token verification

@router.post("/api/login", summary="API Login to obtain JWT token")
def api_login(data: LoginRequest):
    """
    API Login by verifying credentials and providing an access token.
    """
    email = data.emailUser
    password = data.passwordUser
    searched_user = db['Users'].find_one({"emailUser": email})

    if not searched_user or not bcrypt.checkpw(password.encode('utf-8'), searched_user['passwordUser'].encode('utf-8')):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")

    token = create_access_token({"sub": searched_user['emailUser']}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return JSONResponse(content={"access_token": token, "token_type": "bearer"})

    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login") 

def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_token(token)

# Routes - Categories and Authors Management
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
def authors_post_page(data: List[Author] = Body(...), current_user = Depends(get_current_user)):
    """
    Create new authors with the provided data.
    This route is accessible only with a valid JWT token.
    """
    user = db['Users'].find_one({"emailUser": current_user["sub"]})

    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    
    try:
        for author_data in data:
            # Insert each author into the Authors collection
            authors_collection.insert_one(author_data.dict())  # Use `.dict()` to get the model data as a dictionary
        # Fetch all authors after insertion
        authors = authors_collection.find()
        authors_dict = []

        # Convert MongoDB documents to a JSON serializable format
        for author in authors:
            author_dict = dict(author)
            author_dict["_id"] = str(author["_id"])  # Convert ObjectId to string
            authors_dict.append(author_dict)

        return {"authors": authors_dict}  # Return the list of authors as response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/authors", summary="Delete method for Author by ID")
def delete_author_by_id(author_id: str = Form(...), current_user = Depends(get_current_user)):
    """
    Delete an author by their ID using a form submission.
    This route is accessible only with a valid JWT token.
    """
    # Get the user from the JWT token
    user = db['Users'].find_one({"emailUser": current_user["sub"]})

    # Check if the user has admin privileges
    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")

    try:
        # Convert the author_id string to ObjectId
        author_object_id = ObjectId(author_id)

        # Delete the author with the given ObjectId
        result = authors_collection.delete_one({"_id": author_object_id})

        if result.deleted_count == 0:
            # If no author is deleted, raise a 404 exception
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    except Exception as e:
        # Raise an internal server error if something goes wrong
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"message": f"Author with ID '{author_id}' deleted successfully."}

@router.get("/categories")
async def get_categories():
    """
    Fetches all categories and returns them in a list.
    """
    try:
        categories = list(categories_collection.find({}, {"_id": 1, "nameCategory": 1}))
        return [
            {
                "_id": str(category["_id"]), 
                "nameCategory": category["nameCategory"]
             }
            for category in categories
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/categories", summary="Post method for Categories")
def categories_post_page(data: List[Category] = Body(...), current_user = Depends(get_current_user)):
    """
    Create new categories with the provided data.
    This route is accessible only with a valid JWT token.
    """
    user = db['Users'].find_one({"emailUser": current_user["sub"]})

    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")
    try:
        # Insert each category into the Categories collection
        for category_data in data:
            categories_collection.insert_one(category_data.dict()) 

        # Fetch all categories after insertion
        categories = categories_collection.find()

        categories_dict = []
        for category in categories:
            category["_id"] = str(category["_id"])
            categories_dict.append(category)

        return {"categories": categories_dict}  # Return the list of categories as response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/categories", summary="Delete method for Category by Name")
def delete_category_by_name(nameCategory: str = Form(...), current_user = Depends(get_current_user)):
    """
    Delete a category by its name.
    This route is accessible only with a valid JWT token.
    """
    # Get the user from the JWT token
    user = db['Users'].find_one({"emailUser": current_user["sub"]})

    # Check if the user has admin privileges
    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed")

    try:
        # Delete the category with the given name
        result = categories_collection.delete_one({"nameCategory": nameCategory})

        if result.deleted_count == 0:
            # If no category is deleted, raise a 404 exception
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    except Exception as e:
        # Raise an internal server error if something goes wrong
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"message": f"Category with name '{nameCategory}' deleted successfully."}

@router.get("/api/rents", summary="List of Rents")
def get_rents(current_user=Depends(get_current_user)):
    """
    API endpoint to retrieve rents.
    Admin users get all rents, while regular users only get their own rents.
    """
    histories_collection = db["Histories"]

    # Get the user from the JWT token
    user = db["Users"].find_one({"emailUser": current_user["sub"]})

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Define the aggregation pipeline
    pipeline = [
        {
            "$lookup": {
                "from": "Users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {
            "$lookup": {
                "from": "Books",
                "localField": "book_id",
                "foreignField": "_id",
                "as": "book",
            }
        },
        {"$unwind": "$user"},
        {"$unwind": "$book"},
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "user_id": {"$toString": "$user_id"},
                "book_id": {"$toString": "$book_id"},
                "dateLoan": 1,
                "dateReturn": 1,
                "isReturned": 1,
                "username": "$user.emailUser",
                "bookName": "$book.nameBook",
            }
        },
        {"$sort": {"isReturned": 1, "dateLoan": -1}},
    ]

    # Check if the user is an admin
    if user.get("is_admin"):
        # Admin: Fetch all rents
        rents = histories_collection.aggregate(pipeline)
    else:
        # Regular user: Filter rents by the current user's ID
        pipeline.insert(0, {"$match": {"user_id": user["_id"]}})
        rents = histories_collection.aggregate(pipeline)

    # Convert the result to a list
    rents_list = list(rents)

    return JSONResponse(content={"rents": rents_list})