from flask import Blueprint, redirect, render_template, request, url_for, jsonify, json, Response
from flask_login import current_user
from .. import db
import random
import uuid



#Game Bp
play_bp = Blueprint('play', __name__, url_prefix='/play')

@play_bp.route('/game/', methods = ['POST', 'GET'])
@play_bp.route('/game/<game_id>', methods = ['POST', 'GET'])
def game(game_id=None):
    # If game_id provided, validate it exists or will be loaded from DB/PENDING
    # If not provided, socket.io will handle matchmaking in join_game
    return render_template('game.html', game_id=game_id or '')


### Source of Initialisation. Called when no pending games available.
@play_bp.route("/create_game", methods=['GET'])
def create_game():
    """Generate a new game_id and add to PENDING_GAME_STATES.
    
    The client will then navigate to game.html which will emit join_game
    without a game_id, triggering matchmaking logic.
    """
    from .game_socket import PENDING_GAME_STATES, init_game_state
    
    game_id = str(uuid.uuid4())[:12]  # e.g. "a93b1c2d8ef0"
    PENDING_GAME_STATES[game_id] = init_game_state()
    
    # Redirect to game.html with the new game_id
    return redirect(url_for('play.game', game_id=game_id))


def get_piece(piece_dict: dict) -> str:
    revealed_piece = None
    try:
        revealed_piece = str(random.choice(list(piece_dict.keys())))
        piece_dict[revealed_piece] -= 1
        if piece_dict[revealed_piece] == 0:
            del piece_dict[revealed_piece]
    except IndexError:
        return "none"
    except KeyError:
        return "none"   #Temp funct to return none, should be changed to 404 as this shouldn't occur.
    except Exception:
        return "none"
    return str(revealed_piece)

def init_piece_pool()-> dict:
    piece_dict = dict(w_king=1, b_king=1,
     w_advisor=2, b_advisor=2,
     w_elephant=2, b_elephant=2,
     w_chariot=2, b_chariot=2,
     w_horse=2, b_horse=2,
     w_pawn=5, b_pawn=5,
     w_catapult=2, b_catapult=2)
    return piece_dict

###
def init_pos() -> dict:
    return {
        f"{str(file)}{int(rank)}": "unknown"
        for file in "abcdefgh"
        for rank in range(1, 5)
    }

