from flask import Blueprint, redirect, render_template, request, url_for, jsonify, json
from flask_login import current_user
from .. import db
import random

#Game Bp
play_bp = Blueprint('play', __name__, url_prefix='/play')
@play_bp.route('/game', methods = ['POST', 'GET'])
def game():
    return render_template('game.html')

#init game board upon loading the game.
@play_bp.route('/initialise')
def initialise() -> dict:
    pos = init_pos()    #get piece_dict, and return a dict of game map where pieces are assigned as "unknown".
    return jsonify(pos)     # return pos to json.


def get_piece() -> str:
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
