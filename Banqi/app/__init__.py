from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import secrets
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user

socketio = SocketIO(async_mode='threading', cors_allowed_origins="*", manage_session=True)
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banqi_db.sqlite'

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # set login view (type-checker will complain; suppress with type: ignore)
    login_manager.login_view = 'auth.login'  # type: ignore

    # register blueprints
    from .routes.views import main_bp
    app.register_blueprint(main_bp)

    from .routes.home import home_bp
    app.register_blueprint(home_bp)

    from .routes.game import play_bp
    app.register_blueprint(play_bp)

    # auth blueprint
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # import socket handlers (module-level registers)
    from .routes import game_socket

    # make current_user available in templates
    @app.context_processor
    def inject_user():
        return { 'current_user': current_user }

    # load user by id for session management (required for persistent login)
    @login_manager.user_loader
    def load_user(user_id: str):
        from .routes.models import User
        return db.session.get(User, int(user_id))

    socketio.init_app(app)
    return app