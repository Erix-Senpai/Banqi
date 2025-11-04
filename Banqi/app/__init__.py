from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
import secrets

db = SQLAlchemy()
def create_app():
    app = Flask(__name__)
    Bootstrap5(app)

    app.secret_key = 'somerandomvalue'

    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banqi_db.sqlite'
    db.init_app(app)

    from .routes.views import main_bp
    app.register_blueprint(main_bp)
    from .routes.home import home_bp
    app.register_blueprint(home_bp)
    
    return app