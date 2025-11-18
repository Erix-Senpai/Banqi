from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import secrets
from flask_socketio import SocketIO

socketio = SocketIO(async_mode='threading')
#cors_allowed_origins="*"
db = SQLAlchemy()
def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = secrets.token_hex(16)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banqi_db.sqlite'
    db.init_app(app)
    
    from .routes.views import main_bp
    app.register_blueprint(main_bp)

    from .routes.home import home_bp
    app.register_blueprint(home_bp)

    from .routes.game import play_bp
    app.register_blueprint(play_bp)
    
    from .routes import game_socket

    socketio.init_app(app)
    return app