from flask import Blueprint, redirect, render_template, request, url_for, jsonify, json, Response
from flask_login import current_user
from .. import db
import random
import uuid



#Game Bp
play_bp = Blueprint('play', __name__, url_prefix='/play')
@play_bp.route('/game/<game_id>', methods = ['POST', 'GET'])
def game(game_id):
    return render_template('game.html', game_id=game_id)


### Source of Initialisation. Currently called from base.html on play.
@play_bp.route("/create_game", methods=['GET'])
def create_game():
    ## On initialise, generate game_id.
    game_id = str(uuid.uuid4())[:12]  # e.g. "a93b1c2d8ef0"
    #active_games[game_id] = GameState(game_id)

    ### Currently immediately redirects to start game. Should be modified to wait for 2nd player to join to start_game.
    return redirect(url_for('play.start_game', game_id=game_id))

### calls from create_game. Once game is created, start game.
@play_bp.route('/start_game', methods=['GET'])
def start_game():
    game_id = request.args.get("game_id")
    ### Currently does not pass through any user data.
    return redirect(url_for('play.game', game_id=game_id))


def get_piece() -> str:
    revealed_piece = None
    try:
        while(1):
            revealed_piece = str(random.choice(list(piece_dict.keys())))
            if piece_dict[revealed_piece] == 0:
                del piece_dict[revealed_piece]
            else:
                piece_dict[revealed_piece] -= 1
                break
    except IndexError:
        return "none"
    except KeyError:
        return "none"   #Temp funct to return none, should be changed to 404 as this shouldn't occur.
    return str(revealed_piece)


###
def init_pos() -> dict:
    global piece_dict
    piece_dict = dict(w_king=1, b_king=1,
     w_advisor=2, b_advisor=2,
     w_elephant=2, b_elephant=2,
     w_chariot=2, b_chariot=2,
     w_horse=2, b_horse=2,
     w_pawn=5, b_pawn=5,
     w_catapult=2, b_catapult=2)
    return {
        f"{str(file)}{int(rank)}": "unknown"
        for file in "abcdefgh"
        for rank in range(1, 5)
    }

active_games = {}  # game_id -> GameState instance


class GameState:
    def __init__(self, game_id):
        self.id = game_id
        self.players = []
        self.board = {}
        self.colours = {}
        self.turn = None
        self.status = "waiting"

