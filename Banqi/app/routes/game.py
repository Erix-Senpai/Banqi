from flask import Blueprint, redirect, render_template, request, url_for, jsonify, json, Response
from flask_login import current_user
from .. import db
import random
import uuid
from .game_socket import active_games
from .game_socket import Game_State, active_games

#Game Bp
play_bp = Blueprint('play', __name__, url_prefix='/play')

@play_bp.route('/game/', methods = ['POST', 'GET'])
@play_bp.route('/game/<game_id>', methods = ['POST', 'GET'])
def game(game_id = None):
    # If game_id provided, validate it exists or will be loaded from DB/PENDING
    # If not provided, socket.io will handle matchmaking in join_game
    is_private = False
    # Itentify is game already exists. If it does, check for if it's private.
    if game_id:
        game_state = active_games.get(game_id)
        if game_state:
            is_private = game_state.is_private
            print(f"validating is_private... {is_private}")
    return render_template('game.html', game_id=game_id or '', is_private=is_private)


### Source of Initialisation. Called when no pending games available.
## REDUNDANT
@play_bp.route("/create_game", methods=['GET'])
def create_game():
    """Generate a new game_id and add to pending_game_states.
    
    The client will then navigate to game.html which will emit join_game
    without a game_id, triggering matchmaking logic.
    """
    
    game_id = str(uuid.uuid4())[:12]  # e.g. "a93b1c2d8ef0"
    game = Game_State(game_id)
    active_games[game_id] = game
    
    # Redirect to game.html with the new game_id
    return redirect(url_for('play.game', game_id=game_id))

@play_bp.route("/create_private_game", methods=['GET'])
def create_private_game():
    game_id = str(uuid.uuid4())[:12]  # e.g. "a93b1c2d8ef0"
    game = Game_State(game_id)
    active_games[game_id] = game
    game.is_private = True
    
    print(f"Created game for game_id{game_id}. Private: {game.is_private}")
    return redirect(url_for('play.game', game_id=game_id))

@play_bp.route("/spectate", methods=["GET", "POST"])
def spectate():
    return render_template("spectate.html")


###
