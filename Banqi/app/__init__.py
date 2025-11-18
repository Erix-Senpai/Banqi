from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import secrets
from flask_socketio import SocketIO

socketio = SocketIO()
#cors_allowed_origins="*"
db = SQLAlchemy()
def create_app():
    app = Flask(__name__)
    socketio.init_app(app)
    app.secret_key = 'somerandomvalue'

    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banqi_db.sqlite'
    db.init_app(app)
    socketio.init_app(app)
    
    from .routes.views import main_bp
    app.register_blueprint(main_bp)

    from .routes.home import home_bp
    app.register_blueprint(home_bp)

    from .routes.game import play_bp
    app.register_blueprint(play_bp)
    
    from .routes import socket

    return app