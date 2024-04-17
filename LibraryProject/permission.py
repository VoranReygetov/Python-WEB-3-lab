from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User

# Define your SQLAlchemy engine
engine = create_engine("sqlite:///./sql_app.db")

# Create a sessionmaker bound to the engine
Session = sessionmaker(bind=engine)

# Create a session
session = Session()

user = input("Write email: ")
# Query the database to retrieve the user you want to update
user_to_update = session.query(User).filter_by(emailUser=user).first()

# Check if the user exists
if user_to_update:
    # Modify the attributes of the user object
    user_to_update.is_admin = True
    # Commit the changes to the database session
    session.commit()
else:
    print("User not found")
