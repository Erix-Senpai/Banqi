import random
from enum import auto, Enum

class GAME_STATUS(Enum):
    STARTING = auto()
    ONGOING = auto()
    FINISHED = auto()

class GAME_RESULT(Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"

PIECE_NOTATION_LIST = {
    'b_king': 'bK',
    'b_advisor': 'bA',
    'b_elephant': 'bE',
    'b_chariot': 'bR',
    'b_horse': 'bH',
    'b_catapult': 'bC',
    'b_pawn': 'bP',
    'w_king': 'rK',
    'w_advisor': 'rA',
    'w_elephant': 'rE',
    'w_chariot': 'rR',
    'w_horse': 'rH',
    'w_catapult': 'rC',
    'w_pawn': 'rP'
}

PLAYER_TURN_TOGGLE = {'A': 'B', 'B': 'A'}

def INIT_POS() -> dict:
    return {
        f"{str(file)}{int(rank)}": "unknown"
        for file in "abcdefgh"
        for rank in range(1, 5)
    }

def INIT_PIECE_POOL()-> dict:
    piece_dict = dict(w_king=1, b_king=1,
     w_advisor=2, b_advisor=2,
     w_elephant=2, b_elephant=2,
     w_chariot=2, b_chariot=2,
     w_horse=2, b_horse=2,
     w_pawn=5, b_pawn=5,
     w_catapult=2, b_catapult=2)
    return piece_dict

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
