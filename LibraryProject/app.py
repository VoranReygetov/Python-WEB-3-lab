# app.py
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.openapi.utils import get_openapi

from config import SECRET_KEY
from auth import authenticate_user, create_access_token
from db import db
from routes import router as api_router

app = FastAPI(swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"})

app.include_router(api_router)

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
        "url": "https://static.vecteezy.com/system/resources/previews/004/852/937/large_2x/book-read-library-study-line-icon-illustration-logo-template-suitable-for-many-purposes-free-vector.jpg"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi

@app.get("/", summary="Redirect to login page")
def main():
    return RedirectResponse("/login")
