from flask_socketio import emit
from .game import get_piece
from .. import socketio
from enum import Enum, auto
import re

@socketio.on("reveal_piece")
def reveal_piece(data):
    square = data["square"]
    revealed_piece = get_piece()

    # Send the revealed piece to ONLY this client
    emit("piece_revealed", {
        "square": square,
        "piece": revealed_piece
    })

@socketio.on("Player_A")
def Player_A(data):
    user_name = ""
    colour = ""
    emit("Player_A_Data", {
        "user_name": user_name,
        "colour": colour
    })

@socketio.on("Player_B")
def Player_B(data):
    user_name = ""
    colour = ""
    emit("Player_B_Data", {
        "user_name": user_name,
        "colour": colour
    })

@socketio.on("is_capturable")
def is_capturable(data):
    print(f'DATA RECEIVED IN IS_CAPTURABLE: {data}. individual data: {data["square1"]}, {data["square2"]}, {data["piece1"]}, {data["piece2"]}')
    result = capturable(data["square1"], data["square2"], data["piece1"], data["piece2"])
    print(result)
    return result


def capturable(square1, square2, piece1, piece2):
    try:
        piece1 = parse_piece(piece1)
        piece2 = parse_piece(piece2)
        print(f"can capture? {can_capture(piece1, piece2)}")
        print(f"is_adjacent? {is_adjacent(square1, square2)}")
        return (can_capture(piece1, piece2) and is_adjacent(square1,square2))
    except Exception as e:
        return False

class PieceType(Enum):
    w_king = auto()
    w_advisor = auto()
    w_elephant = auto()
    w_chariot = auto()
    w_catapult = auto()
    w_horse = auto()
    w_pawn = auto()

    b_king = auto()
    b_advisor = auto()
    b_elephant = auto()
    b_chariot = auto()
    b_catapult = auto()
    b_horse = auto()
    b_pawn = auto()
    

# Capture rules: attacker → list of capturable defender types
CAPTURE_RULES = {
    PieceType.b_king: {PieceType.w_king, PieceType.w_advisor, PieceType.w_elephant, PieceType.w_chariot, PieceType.w_catapult, PieceType.w_horse},
    PieceType.b_advisor: {PieceType.w_advisor, PieceType.w_elephant, PieceType.w_chariot, PieceType.w_catapult, PieceType.w_horse, PieceType.w_pawn},
    PieceType.b_elephant: {PieceType.w_elephant, PieceType.w_chariot, PieceType.w_catapult, PieceType.w_horse, PieceType.w_pawn},
    PieceType.b_chariot:     {PieceType.w_chariot, PieceType.w_catapult, PieceType.w_horse, PieceType.w_pawn},
    PieceType.b_catapult: {PieceType.w_king, PieceType.w_advisor, PieceType.w_elephant, PieceType.w_chariot, PieceType.w_catapult, PieceType.w_horse, PieceType.w_pawn},
    PieceType.b_horse: {PieceType.w_catapult, PieceType.w_horse, PieceType.w_pawn},
    PieceType.b_pawn: {PieceType.w_pawn, PieceType.w_king},
    PieceType.w_king: {PieceType.b_king, PieceType.b_advisor, PieceType.b_elephant, PieceType.b_chariot, PieceType.b_catapult, PieceType.b_horse},
    PieceType.w_advisor: {PieceType.b_advisor, PieceType.b_elephant, PieceType.b_chariot, PieceType.b_catapult, PieceType.b_horse, PieceType.b_pawn},
    PieceType.w_elephant: {PieceType.b_elephant, PieceType.b_chariot, PieceType.b_catapult, PieceType.b_horse, PieceType.b_pawn},
    PieceType.w_chariot:     {PieceType.b_chariot, PieceType.b_catapult, PieceType.b_horse, PieceType.b_pawn},
    PieceType.w_catapult: {PieceType.b_king, PieceType.b_advisor, PieceType.b_elephant, PieceType.b_chariot, PieceType.b_catapult, PieceType.b_horse, PieceType.b_pawn},
    PieceType.w_horse: {PieceType.b_catapult, PieceType.b_horse, PieceType.b_pawn},
    PieceType.w_pawn: {PieceType.b_pawn, PieceType.b_king}

}
def can_capture(attacker: PieceType, defender: PieceType) -> bool:
    return defender in CAPTURE_RULES.get(attacker, set())

def parse_piece(piece_str: str) -> PieceType:
    return PieceType[piece_str]    # works if enum names match EXACTLY

def square_to_coord(square: str) -> tuple[int, int]:
    col = ord(square[0]) - ord('a') + 1  # 'a'→1, 'b'→2 ... 'h'→8
    row = int(square[1])     # '1'→1, '4'→4
    return (col, row)

def is_adjacent(sq1: str, sq2: str) -> bool:
    col1, row1 = square_to_coord(sq1)
    col2, row2 = square_to_coord(sq2)

    # orthogonal neighbors:
    print(f"{col1}? - {col2}? == 1? and {row1}? == {row2}? or {row1}? - {row2} == 1? and {col1}? == {col2} ?")
    return (abs(col1 - col2) == 1 and row1 == row2) or \
           (abs(row1 - row2) == 1 and col1 == col2)
