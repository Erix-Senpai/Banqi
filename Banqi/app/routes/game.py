from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user
from .. import db
import random
play_bp = Blueprint('play', __name__, url_prefix='/play')
@play_bp.route('/game', methods = ['POST', 'GET'])
def game():
    return render_template('game.html')




def board(__from__, __to__, status):
    if status == 'start':
        populate()

def populate():
    return

pieces = dict(w_general=1, b_general=1,
     w_advisor=2, b_advisor=2,
     w_elephant=2, b_elephant=2,
     w_chariot=2, b_chariot=2,
     w_horse=2, b_horse=2,
     w_pawn=5, b_pawn=5,
     w_catapult=2, b_catapult=2)

pool = [piece for piece, count in pieces.items() for _ in range(count)]
random.shuffle(pool)

class initialise_Board:
    def __dict__():
        files = {
            1:'a',
            2:'b',
            3:'c',
            4:'d',
            5:'e',
            6:'f',
            7:'g',
            8:'h'
        }
    def __init__():
        pieces == 'unknown'
        pos = []
        for i in range(8):
            for y in range(4):
                x = [i[file] for file in __dict__.files if file in i]
                pos.append(x,y)
        return pos

def position():
    
    a1 = initialise_Board
    print(a1)