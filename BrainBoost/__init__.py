from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import os

app = Flask(__name__)

app.config[
    "SECRET_KEY"
] = "da1e2c76500b711f5b9ae6476fc1e56c842d761b7bbd38f6b51ad25a76fd8bc4"

db_path = os.path.join(os.getcwd(), "instance", "brainboost.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True


db = SQLAlchemy(app)

app.app_context().push()

bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"
#upload file code
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}



from BrainBoost import routes
