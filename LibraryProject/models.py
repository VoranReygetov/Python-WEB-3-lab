from pydantic import BaseModel, Field
from bson import ObjectId


class LoginRequest(BaseModel):
    emailUser: str
    passwordUser: str

class RegistrationRequest(BaseModel):
    nameUser: str = Field(..., max_length=100)
    surnameUser: str = Field(..., max_length=100)
    emailUser: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    passwordUser: str = Field(..., min_length=8)
    numberUser: str = Field(..., min_length=10, max_length=15)

class BookRequest(BaseModel):
    id: str
    nameBook: str
    yearBook: int
    availableBook: int
    category_id: str  # this will be an ObjectId in MongoDB, but for the model, it can be a string
    author_id: str    # this will be an ObjectId in MongoDB, but for the model, it can be a string

    class Config:
        # Allow to convert str to ObjectId when using the model
        orm_mode = True
    
class Author(BaseModel):
    nameAuthor: str = Field(..., example="George")
    surnameAuthor: str = Field(..., example="Orwell")

# Updated Category model to match your data structure
class Category(BaseModel):
    nameCategory: str = Field(..., example="Child")