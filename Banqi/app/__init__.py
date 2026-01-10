from flask import Flask, render_template
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

    socketio.init_app(app)

    # Now that Socket.IO server is initialized, start any background tasks
    # defined in the socket handlers (e.g. disconnect watcher).
    try:
        socketio.start_background_task(game_socket.disconnect_watcher, app)
    except Exception:
        # be tolerant if background task cannot be started in this environment
        pass

    return app