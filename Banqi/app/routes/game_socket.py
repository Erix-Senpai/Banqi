from flask_socketio import emit, join_room, leave_room
from .game import get_piece
from .. import socketio
from enum import Enum, auto
from ..routes.game import init_pos
from flask import request
from flask_login import current_user

GAME_STATES = {}
piece_list = {
    "bK":'b_king', "bA": 'b_advisor', "bE": 'b_elephant', "bR": 'b_chariot', "bH": 'b_horse', "bC": 'b_catapult', "bP": 'b_pawn',
    "rK":'w_king', "rA": 'w_advisor', "rE": 'w_elephant', "rR": 'w_chariot', "rH": 'w_horse', "rC": 'w_catapult', "rP": 'w_pawn'
}
###
@socketio.on("fetch_game")
def fetch_game(game_id: str):
    return GAME_STATES.get(game_id)
@socketio.on("player_turn")
def get_player_turn(data):
    game_id = data["game_id"]
    return GAME_STATES[game_id]["player_turn"]
@socketio.on("current_player")
def return_current_player(game_id):
    return GAME_STATES[game_id]["current_player"]
@socketio.on("move_count")
def return_move_count(game_id):
    return GAME_STATES[game_id]["move_count"]
    

@socketio.on("reveal_piece")
def reveal_piece(data:dict) -> dict:
    result = {"validity": False}
    try:
        game_id = data["game_id"]
        game = GAME_STATES[game_id]
        square = data["square"]
        if not (game["board"][square] == "unknown"):
            return result
        #if not (validate_user(game_id)):
        #    return result
        #NOTE: We temporarily don't validate the user yet. We treat both player as 1 singular.
        revealed_piece = get_piece()
        if not game["players"]["A"]["colour"]:
            set_player_colour(game_id, revealed_piece[0])
            
        if (revealed_piece == "none"):#Error Handlning for case where result == "none"
            return result
        
        result = {"validity": True, "square": square, "piece": revealed_piece}
        GAME_STATES[game_id]["board"][square] = revealed_piece
        notation = (f"{square} = ({piece_list.get(revealed_piece)})")
        record_move(game_id, notation)
        return result
    except Exception:
        return result

@socketio.on("make_move")
def make_move(data: dict) -> dict:
    result = {"validity": False}
    try:
        game_id = data["game_id"]
        game = GAME_STATES[game_id]
        board = game["board"]
        sq1 = data["square1"]
        sq2 = data["square2"]
        piece = data["piece"]
        current_player = game["current_player"]
        #if not (validate_user(game_id)):
        #    return result
        print("Attempting to Move.")
        print(f"Testing.")
        print(f"Sq1: {sq1}, p1: {piece}.")
        print(f"Sq2: {sq2}, p2: {board[sq2]}.")
        print("testing for Movement validity.")
        print(f"is_adjacent? {is_adjacent(sq1, sq2)}")
        print(f"board[sq1] == piece? {board[sq1] == piece}")
        print(f"board[sq2] == none? {board[sq2] == "none"}")
        print(f"{piece[0]} == {game["players"][current_player]["colour"]} ?")
        a = piece[0] == game["players"][current_player]["colour"]
        print("piece[0] == game..current_player.colour? {a}")

        if (
            is_adjacent(sq1, sq2) and
            board[sq1] == piece and
            board[sq2] == "none" and
            piece[0] == game["players"][current_player]["colour"]
            ):
            print("true!")
            result = {"validity": True, "square1": sq1, "square2": sq2, "piece": piece}
            GAME_STATES[game_id]["board"][sq1] = "none"
            GAME_STATES[game_id]["board"][sq2] = piece
            notation = (f"{sq1} - {sq2}")
            record_move(game_id, notation)
            return result
        return result
    except Exception:
        return result

@socketio.on("capture")
def capture(data: dict) -> dict:
    result = {"validity": False}
    try:
        game_id = data["game_id"]
        game = GAME_STATES[game_id]
        board = game["board"]
        sq1 = data["square1"]
        sq2 = data["square2"]
        p1 = data["piece1"]
        p2 = data["piece2"]
        current_player = game["current_player"]
        print(f"Testing. Sq1: {sq1}, p1: {p1}.")
        print(f"Sq2: {sq2}, p2: {p2}.")
        print(f"Sq1: {sq1}, p1: {p1}.")
        print("testing for Capture validity.")
        print(f"{board[sq1][0]} == {game["players"][current_player]["colour"]} ?")
        if not (
            board[sq1] == p1 and board[sq2] == p2):
            return result
        if (
            capturable(sq1, sq2, p1, p2) and
            board[sq1][0] == game["players"][current_player]["colour"] and
            board[sq2][0] != "n" and
            board[sq2][0] != game["players"][current_player]["colour"]
                ):
            result = {"validity": True, "square1": sq1, "square2": sq2, "piece1": p1, "piece2": p2}
            GAME_STATES[game_id]["board"][sq1] = "none"
            GAME_STATES[game_id]["board"][sq2] = p1
            notation = (f"{sq1} x {sq2}")
            record_move(game_id, notation)
            return result
        print("failed.")
        print("^^^^^^")
        return result
    except Exception:
        return result


def validate_user(game_id: str)-> bool:
    try:
        game = GAME_STATES[game_id]
        user_id = current_user.id
        return game["players"]["current_player"]["user_id"] == user_id
    except Exception:
        return False

def record_move(game_id: str, notation: str)->None:
    if (GAME_STATES[game_id]["current_player"] == "A"):
        GAME_STATES[game_id]["moves"]["A"].append(notation)
        player_turn = "A"
        GAME_STATES[game_id]["current_player"] = "B"
    else:
        GAME_STATES[game_id]["moves"]["B"].append(notation)
        GAME_STATES[game_id]["current_player"] = "A"
        player_turn = "B"
    socketio.emit("render_move",{"game_id": game_id, "notation": notation, "player_turn": player_turn})


def set_player_colour(game_id: str, colour_a :str) -> None:
    GAME_STATES[game_id]["players"]["A"]["colour"] = colour_a
    if (colour_a == "w"):
        GAME_STATES[game_id]["players"]["B"]["colour"] = "b"
    else:
        GAME_STATES[game_id]["players"]["B"]["colour"] = "w"


@socketio.on("join_game")
def join_game(data: dict) -> None:
    game_id = data["game_id"]
    user_id = 1
    username = "test"
    sid = request.sid # type: ignore
    if game_id not in GAME_STATES:
        GAME_STATES[game_id] = init_game_state()
        print(f"[NEW GAME] initialised board for game {game_id}")
    else:
        print(f"[LOAD GAME] sending existing board for game {game_id}")
    
        # Else user is in spectator Mode, Cannot make any action.
    # Else game is inactive, currently do not have a Function for it.
    game = GAME_STATES[game_id]
    join_room(game_id)
    try:

        if (game["status"] == "Active"):
            if (game["players"]["A"]["user_id"] == None):
                game["players"]["A"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
                game["players"]["B"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
                # WARNING / NOTE: ABOVE [B] NEEDS TO GET RID!!!
                print("player successfully added.")
            elif ((game["players"]["B"]["user_id"]) == None):
                game["players"]["B"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
            ## Else, the player is a spectator. They could try make a move, but will always be invalid.
    except Exception:
        leave_room(game_id)
    socketio.emit("joined_game", {
        "game_id": game_id,
        "board": GAME_STATES[game_id]["board"]
        },
        room=sid) # type: ignore


def capturable(square1: str, square2: str, piece1: str, piece2: str) -> bool:
    try:
        p1 = parse_piece(piece1)
        p2 = parse_piece(piece2)
        print(f"can capture? {can_capture(p1, p2)}")
        print(f"is_adjacent? {is_adjacent(square1, square2)}")
        return (can_capture(p1, p2) and is_adjacent(square1,square2))
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

def is_same_array(sq1: str, sq2: str) -> bool:
    col1, row1 = square_to_coord(sq1)
    col2, row2 = square_to_coord(sq2)

    return (2 <= abs(col1 - col2) and row1 == row2) or \
            (2 <= abs(row1 - row2) and col1 == col2)

def init_game_state():
    return {
        "board": init_pos(),
        "player_turn": "A",
        "current_player": "A",
        "move_count": 0,
        "players": {
            "A": {"user_id": None, "sid": None, "username": None, "colour": None},
            "B": {"user_id": None, "sid": None, "username": None, "colour": None}
        },
        "moves": {
            "A": [],
            "B": []
        },
        "status": "Active"
    }
