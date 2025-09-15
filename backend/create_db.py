from .database import Base, engine
from . import models # Import models to ensure they are registered with Base

def create_db_tables():
    Base.metadata.drop_all(bind=engine) # Drop all existing tables
    Base.metadata.create_all(bind=engine)
    print("Database tables recreated!")

if __name__ == "__main__":
    create_db_tables()
