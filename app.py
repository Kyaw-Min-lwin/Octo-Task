from flask import Flask
from extensions import db
from flask_migrate import Migrate
import models
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)
migrate = Migrate(app, db)  

@app.route("/")
def home():
    return "Flask + PostgreSQL is working!"


if __name__ == "__main__":
    app.run(debug=True)
