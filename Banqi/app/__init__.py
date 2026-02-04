from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import secrets
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask import session
import uuid
import random

socketio = SocketIO(cors_allowed_origins="*", manage_session=True, async_mode="threading")
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

    # spectate blueprint
    from .routes.spectate import spectate_bp
    app.register_blueprint(spectate_bp)

    # auth blueprint
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # import socket handlers (module-level registers)
    # NOTE: do NOT start background tasks from the module import; the tasks
    # that rely on `socketio` being initialized are started after calling
    # `socketio.init_app(app)` below.
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
    
    @app.errorhandler(404) 
    # inbuilt function which takes error as parameter 
    def not_found(e): 
      return render_template("404.html", error=e)
        
    @app.errorhandler(500) 
    # inbuilt function which takes error as parameter 
    def internal_error(e): 
      return render_template("500.html", error=e)
    
    @app.before_request
    def session_identity():
        if current_user.is_authenticated:
            session["user_id"] = current_user.id
            session["username"] = current_user.username
            session["is_guest"] = False
        else:
            if "user_id" not in session:
                session["user_id"] = str(uuid.uuid4())[:8]

                session["username"] = f"ANON_{str(uuid.uuid4())[:4]}{random.randint(1000,9999)}"
                session["is_guest"] = True

    socketio.init_app(app)

    # Now that Socket.IO server is initialized, start any background tasks
    # defined in the socket handlers (e.g. disconnect watcher).
    try:
        socketio.start_background_task(game_socket.disconnect_watcher, app)
    except Exception:
        # be tolerant if background task cannot be started in this environment
        pass

    return app