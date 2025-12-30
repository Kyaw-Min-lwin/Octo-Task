import os
from dotenv import load_dotenv

load_dotenv()
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")

SQLALCHEMY_TRACK_MODIFICATIONS = False
