from fastapi import Depends, FastAPI, Body, HTTPException, status, Response, Cookie
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader
from fastapi.openapi.utils import get_openapi
import psycopg2
from contextlib import contextmanager
import json
from datetime import datetime

#enviroment for jinja2
file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)

#connection to postgreSQL
@contextmanager
def connection_pstgr():
    """
    Context manager for establishing a connection to the PostgreSQL database.
    """
    conn = psycopg2.connect(
        dbname="libraryproject",
        host="127.0.0.1",
        user="postgres",
        password="password",
        port="5432"
    )
    cursor = conn.cursor()
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

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

def authenticate_user(email: str, password: str):
    """
    Checking in Users table by passed emails to LogIn form.
    """
    with connection_pstgr() as (conn, cursor):
        cursor.execute("SELECT * FROM Users WHERE emailUser = %s", (email,))
        searched_user = cursor.fetchone()
        if searched_user and searched_user[3] == password:
            columns = [desc[0] for desc in cursor.description]
            user_dict = dict(zip(columns, searched_user))
            return user_dict
        else:
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
    with connection_pstgr() as (conn, cursor):
        cursor.execute("SELECT * FROM Users WHERE emailUser = %s", (email,))
        searched_user = cursor.fetchone()
    try:
        if searched_user[3] == password:
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
    with connection_pstgr() as (conn, cursor):
        insert_query = """INSERT INTO Users (nameUser, surnameUser, passwordUser, emailUser, numberUser)
                          VALUES (%s, %s, %s, %s, %s) RETURNING *"""
        try:
            cursor.execute(insert_query, (data["nameUser"], data["surnameUser"], data["passwordUser"], data["emailUser"], data["numberUser"]))
            user = cursor.fetchone()  # Fetch the inserted user data
            conn.commit()
        except:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Registration failed")
    response = JSONResponse(content={"message": f"{user}"})
    response.set_cookie(key="email", value=data.get("emailUser"))
    response.set_cookie(key="password", value=data.get("passwordUser"))
    return response

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
    user = authenticate_user(email, password)
    if user["is_admin"]:
        template_file = 'book-list-roles/admin-book-list.html'
    else:
        template_file = 'book-list-roles/user-book-list.html'

    book_list_page = env.get_template(template_file)
    rents_book_id = []
    with connection_pstgr() as (conn, cursor):
        cursor.execute("""
            SELECT b.id, b.nameBook, b.yearBook, b.availableBook, 
            c.nameCategory as category_name, 
            a.nameAuthor || ' ' || a.surnameAuthor as author_name
            FROM Books b
            JOIN Categories c ON b.category_id = c.id
            JOIN Authors a ON b.author_id = a.id
            ORDER BY b.id;
            """)
        books = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        books_list = []
        for row in books:
            book_dict = dict(zip(columns, row))
            books_list.append(book_dict)

        if not user["is_admin"]:
            cursor.execute("""
                SELECT books_id
                FROM Histories
                WHERE user_id = %s AND isReturned = FALSE
            """, (user["id"],))
            # Fetch all rows from the result set
            rents_book_id = [row[0] for row in cursor.fetchall()]

    # Render the book list page with appropriate data
    output = book_list_page.render(
        books=books_list,
        username=email,
        rents_book_id=rents_book_id
    )
    # Return the book list page
    return output

@app.get("/book/{book_id}", summary="Get for getting one specific book")
def book_page(book_id):
    """
    Retrieves information about a specific book by its ID.
    """
    with connection_pstgr() as (conn, cursor): 
        cursor.execute("SELECT * FROM Books WHERE id = %s", (book_id,))
        book = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]

    if book is None: #якщо не знайдена, відправляємо статусний код і повідомлення про помилку
        return JSONResponse(status_code=404, content={"message": "Книжка не знайдена"})
    
    book_dict = dict(zip(columns, book))
    return book_dict


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
    if user["is_admin"]:
        with connection_pstgr() as (conn, cursor):
            cursor.execute("""
                INSERT INTO Books (nameBook, yearBook, availableBook, category_id, author_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (book_data.get("nameBook"), book_data.get("yearBook"), book_data.get("availableBook"), book_data.get("category_id"), book_data.get("author_id")))
            inserted_book = cursor.fetchone()
            columns = [desc[0] for desc in cursor.description]
            conn.commit()

        book_dict = dict(zip(columns, inserted_book))
        inserted_book_json = json.dumps(book_dict)
        return inserted_book_json
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization failed")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization failed")
    
    with connection_pstgr() as (conn, cursor):
        cursor.execute("""
            UPDATE Books
            SET nameBook = %s, yearBook = %s, availableBook = %s, category_id = %s, author_id = %s
            WHERE id = %s
            RETURNING *
        """, (data.get("nameBook"), data.get("yearBook"), data.get("availableBook"), data.get("category_id"), data.get("author_id"), data.get("id")))
        
        updated_book = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        conn.commit()
    
    book_dict = dict(zip(columns, updated_book))
    updated_book_json = json.dumps(book_dict)
    return updated_book_json

@app.delete("/book/{book_id}", summary="Delete method for Book")
def delete_book(book_id: int, email: str | None = Cookie(default=None), password: str | None = Cookie(default=None)):
    """
    Deletes a book from the library based on its ID.
    """
    user = authenticate_user(email, password)
    if not user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization failed")

    with connection_pstgr() as (conn, cursor):
        cursor.execute("DELETE FROM Books WHERE id = %s RETURNING *", (book_id,))
        deleted_book = cursor.fetchone()

        if deleted_book:
            columns = [desc[0] for desc in cursor.description]
            book_dict = dict(zip(columns, deleted_book))
            conn.commit()
            return book_dict
        else:
            raise HTTPException(status_code=404, detail="Book not found")


@app.post("/book/{book_id}/rent", summary="Renting a book")
def rent_book(
    book_id: int,
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None)
):
    """
    Rent a book for a user.
    """
    date_now = datetime.now()
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    with connection_pstgr() as (conn, cursor):
        # Update existing rental record
        cursor.execute("""
            SELECT * FROM Histories
            WHERE user_id = %s
            AND isReturned = FALSE
            AND books_id = %s
        """, (user['id'], book_id))
        rent = cursor.fetchone()

        if rent:  # Rental record already exists
            cursor.execute("""
                UPDATE Histories
                SET isReturned = TRUE, dateReturn = %s
                WHERE id = %s
            """, (date_now, rent[0]))
            cursor.execute("""
                UPDATE Books
                SET availableBook = availableBook + 1
                WHERE id = %s
            """, (book_id,))
        else:  # Create a new rental record
            try:
                cursor.execute("""
                    INSERT INTO Histories (user_id, books_id, dateLoan, isReturned)
                    VALUES (%s, %s, %s, FALSE)
                """, (user['id'], book_id, date_now))
                cursor.execute("""
                    UPDATE Books
                    SET availableBook = availableBook - 1
                    WHERE id = %s
                """, (book_id,))
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        conn.commit()
        return {"message": "Book rented successfully."}

@app.get("/rents-list", summary="List of Rents")
def book_list_page(
    email: str | None = Cookie(default=None),
    password: str | None = Cookie(default=None)
):
    user = authenticate_user(email, password)
    if user:
        output = render_rent_list(user)
        return HTMLResponse(output)
    else:
        return RedirectResponse("/login")

def render_rent_list(user):
    if user["is_admin"]:
        book_list_page = env.get_template('rent-list.html')
        with connection_pstgr() as (conn, cursor):
            cursor.execute("""
                SELECT * FROM Histories
                ORDER BY isReturned ASC, dateLoan DESC
            """)
            rents = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            rents_list = []
            for row in rents:
                rent_dict = dict(zip(columns, row))
                rents_list.append(rent_dict)

            output = book_list_page.render(
                rents=rents_list,
                username=user['emailuser']
            )
    else:
       raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization failed")
    return output

@app.post("/authors", summary="Post method for Authors")
def authors_post_page(data: list[dict] = Body(...)):
    """
    Create new authors with the provided data.
    """
    with connection_pstgr() as (conn, cursor):
        try:
            for author_data in data:
                nameAuthor = author_data.get("nameAuthor")
                surnameAuthor = author_data.get("surnameAuthor")
                # Execute SQL query to insert the new author into the database
                cursor.execute("""
                    INSERT INTO Authors (nameAuthor, surnameAuthor)
                    VALUES (%s, %s)
                """, (nameAuthor, surnameAuthor))
            conn.commit()
            # Fetch all authors after insertion
            cursor.execute("SELECT * FROM Authors")
            authors = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            authors_dict = dict(zip(columns, authors))
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return json.dumps(authors_dict)


@app.post("/categories", summary="Post method for Categories")
def categories_post_page(data: list[dict] = Body(...)):
    """
    Create new categories with the provided data.
    """
    with connection_pstgr() as (conn, cursor):
        try:
            for category_data in data:
                category_name = category_data.get("nameCategory")
                # Execute SQL query to insert the new category into the database
                cursor.execute("""
                    INSERT INTO Categories (nameCategory)
                    VALUES (%s)
                """, (category_name,))
            conn.commit()
            # Fetch all categories after insertion
            cursor.execute("SELECT * FROM Categories")
            categories = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            categories_dict = [dict(zip(columns, category)) for category in categories]
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return json.dumps(categories_dict)


@app.post("/book-list", summary="Post method for Books")
def books_post_page(data: list[dict] = Body(...)):
    """
    Create new books with the provided data.
    """
    with connection_pstgr() as (conn, cursor):
        try:
            for book_data in data:
                nameBook = book_data.get("nameBook")
                yearBook = book_data.get("yearBook")
                availableBook = book_data.get("availableBook")
                category_id = book_data.get("category_id")
                author_id = book_data.get("author_id")
                # Execute SQL query to insert the new book into the database
                cursor.execute("""
                    INSERT INTO Books (nameBook, yearBook, availableBook, category_id, author_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (nameBook, yearBook, availableBook, category_id, author_id))
            conn.commit()
            # Fetch all books after insertion
            cursor.execute("SELECT * FROM Books")
            books = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            books_dict = [dict(zip(columns, book)) for book in books]
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return json.dumps(books_dict)


@app.get("/clear-cookie", summary="Clearing Cookies")
def clear_cookie(response: Response):
    response.delete_cookie("email")
    response.delete_cookie("password")
    return {"message": "Cookie cleared successfully"}