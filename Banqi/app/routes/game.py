from flask import Blueprint, redirect, render_template, request, url_for, jsonify, json
from flask_login import current_user
from .. import db
import random
play_bp = Blueprint('play', __name__, url_prefix='/play')
@play_bp.route('/game', methods = ['POST', 'GET'])
def game():
    return render_template('game.html')


@play_bp.route('/initialise')
def initialise():
    # pretend this is your game state
    pos = init_pos()
    # Flask automatically turns Python dict → JSON
    return jsonify(pos)




pieces = dict(w_general=1, b_general=1,
     w_advisor=2, b_advisor=2,
     w_elephant=2, b_elephant=2,
     w_chariot=2, b_chariot=2,
     w_horse=2, b_horse=2,
     w_pawn=5, b_pawn=5,
     w_catapult=2, b_catapult=2)

pool = [piece for piece, count in pieces.items() for _ in range(count)]
random.shuffle(pool)

def init_pos() -> dict:
    return {
        f"{file}{rank}": "unknown"
        for file in "abcdefgh"
        for rank in range(1, 5)
    }


# print(f"POS: {init_pos()}")
