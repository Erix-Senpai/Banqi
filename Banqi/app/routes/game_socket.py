from flask_socketio import emit, join_room, leave_room
from .game import get_piece
from .. import socketio
from enum import Enum, auto
from ..routes.game import init_pos, init_piece_pool
from flask import request
from flask_login import current_user

from app import db
from .models import Game, Player, Move

GAME_STATES = {}
piece_list = {
    "bK":'b_king', "bA": 'b_advisor', "bE": 'b_elephant', "bR": 'b_chariot', "bH": 'b_horse', "bC": 'b_catapult', "bP": 'b_pawn',
    "rK":'w_king', "rA": 'w_advisor', "rE": 'w_elephant', "rR": 'w_chariot', "rH": 'w_horse', "rC": 'w_catapult', "rP": 'w_pawn'
}
###
@socketio.on("fetch_game")
def fetch_game(game_id: str):
    return GAME_STATES.get(game_id)
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
        revealed_piece = get_piece(game["piece_pool"])
        if not reveal_piece:
            return result
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
        player_turn = game["player_turn"]
        #if not (validate_user(game_id)):
        #    return result
        if (
            is_adjacent(sq1, sq2) and
            board[sq1] == piece and
            board[sq2] == "none" and
            piece[0] == game["players"][player_turn]["colour"]
            ):
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
        player_turn = game["player_turn"]
        if not (
            board[sq1] == p1 and board[sq2] == p2):
            return result
        if (
            capturable(sq1, sq2, p1, p2, board) and
            board[sq1][0] == game["players"][player_turn]["colour"] and
            board[sq2][0] != "n" and
            board[sq2][0] != game["players"][player_turn]["colour"]
                ):
            result = {"validity": True, "square1": sq1, "square2": sq2, "piece1": p1, "piece2": p2}
            GAME_STATES[game_id]["board"][sq1] = "none"
            GAME_STATES[game_id]["board"][sq2] = p1
            notation = (f"{sq1} x {sq2}")
            record_move(game_id, notation)
            return result
        return result
    except Exception:
        return result


def validate_user(game_id: str)-> bool:
    try:
        game = GAME_STATES[game_id]
        user_id = current_user.id
        if user_id == None:
            user_id = 'ANONYMOUS'
        return game["players"]["player_turn"]["user_id"] == user_id
    except Exception:
        return False

def record_move(game_id: str, notation: str)->None:
    game = GAME_STATES[game_id]
    if (game["player_turn"] == "A"):
        game["moves"]["A"].append(notation)
        player_turn = "A"
        game["player_turn"] = "B"
    else:
        game["moves"]["B"].append(notation)
        game["player_turn"] = "A"
        player_turn = "B"
        game["move_count"] += 1
    socketio.emit("render_move",{"game_id": game_id, "notation": notation, "player_turn": player_turn})
    is_checkmate(game_id)


def set_player_colour(game_id: str, colour_a :str) -> None:
    GAME_STATES[game_id]["players"]["A"]["colour"] = colour_a
    if (colour_a == "w"):
        GAME_STATES[game_id]["players"]["B"]["colour"] = "b"
    else:
        GAME_STATES[game_id]["players"]["B"]["colour"] = "w"


@socketio.on("join_game")
def join_game(data: dict) -> None:
    game_id = data.get("game_id")
    user_id = 1
    username = "test"
    sid = request.sid # type: ignore

    if not game_id:
        return

    if game_id not in GAME_STATES:
        # try to load archived game from DB
        loaded = load_game_from_db(game_id)
        if loaded:
            GAME_STATES[game_id] = loaded
        else:
            GAME_STATES[game_id] = init_game_state()

    # Now proceed to join room and register connection
    game = GAME_STATES[game_id]
    join_room(game_id)
    try:
        game.setdefault("connections", set()).add(sid)
    except Exception:
        # defensive: ensure key exists as set
        game["connections"] = set([sid])

    try:
        if game.get("status") == "Active":
            if game["players"]["A"].get("user_id") is None:
                game["players"]["A"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
            elif game["players"]["B"].get("user_id") is None:
                game["players"]["B"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
            # else spectator
    except Exception:
        leave_room(game_id)
        return

    # send current state to joining client only
    socketio.emit("joined_game", {
        "game_id": game_id,
        "board": game.get("board"),
        "moves": game.get("moves"),
        "status": game.get("status"),
        "players": game.get("players")
        },
        room=sid) # type: ignore


@socketio.on("end_game")
def end_game(data: dict) -> None:
    """Socket event to archive a finished game to the database.

    Expects: `{"game_id": "..."}`. This calls `archive_game_to_db()` and
    emits a confirmation to the room for the game.
    """
    try:
        game_id = data.get("game_id")
        if not game_id:
            return
        archive_game_to_db(game_id)
        #TODO: Temporarily commented out to prevent errors during testing.
        #socketio.emit("game_archived", {"game_id": game_id}, room=game_id)
    except Exception:
        # keep handler resilient; callers can check `game_archived` or logs
        return


def capturable(square1: str, square2: str, piece1: str, piece2: str, board: dict) -> bool:
    """Return True if piece1 can capture piece2 according to rules.

    For catapult pieces, capture requires jumping over exactly one intervening
    piece on the same row or column. `board` is the game's board mapping.
    """
    try:
        p1 = parse_piece(piece1)
        p2 = parse_piece(piece2)
        if ("catapult" in piece1):
            return (can_capture(p1, p2) and is_same_array(square1, square2, board))
        return (can_capture(p1, p2) and is_adjacent(square1, square2))
    except Exception:
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
    if not (1 <= col1 <= 8 and 1 <= row1 <= 4 and 1 <= col2 <= 8 and 1 <= row2 <= 4):
        return False
    # orthogonal neighbors:
    return (abs(col1 - col2) == 1 and row1 == row2) or \
           (abs(row1 - row2) == 1 and col1 == col2)

def is_same_array(sq1: str, sq2: str, board: dict) -> bool:
    """Return True if `sq1` and `sq2` are on the same row/column and there
    is exactly one intervening piece between them on `board`.
    """
    try:
        col1, row1 = square_to_coord(sq1)
        col2, row2 = square_to_coord(sq2)
    except Exception:
        return False

    # must be on same row or same column and at least 2 apart
    if row1 == row2 and abs(col1 - col2) >= 2:
        step = 1 if col2 > col1 else -1
        count = 0
        for c in range(col1 + step, col2, step):
            sq = f"{chr(ord('a') + c - 1)}{row1}"
            val = board.get(sq)
            # treat anything other than the explicit empty marker 'none' as a piece
            if val is not None and val != "none":
                count += 1
        return count == 1

    if col1 == col2 and abs(row1 - row2) >= 2:
        step = 1 if row2 > row1 else -1
        count = 0
        for r in range(row1 + step, row2, step):
            sq = f"{chr(ord('a') + col1 - 1)}{r}"
            val = board.get(sq)
            if val is not None and val != "none":
                count += 1
        return count == 1

    return False

def init_game_state():
    return {
        "board": init_pos(),
        "piece_pool": init_piece_pool(),
        "player_turn": "A",
        "move_count": 0,
        "players": {
            "A": {"user_id": None, "sid": None, "username": None, "colour": None},
            "B": {"user_id": None, "sid": None, "username": None, "colour": None}
        },
        "moves": {
            "A": [],
            "B": []
        },
        "status": "Active",
        "winner": None,
        # runtime-only: track connected socket ids (not persisted)
        "connections": set()
    }


def load_game_from_db(game_id: str):
    """Load an archived game from the DB and return an in-memory state dict.

    Returns None if no DB row exists.
    """
    try:
        g = db.session.get(Game, game_id)
        if not g:
            return None

        state = {
            "board": g.board,
            "piece_pool": g.piece_pool,
            "player_turn": g.player_turn,
            "move_count": g.move_count,
            "players": {
                "A": {"user_id": None, "sid": None, "username": None, "colour": None},
                "B": {"user_id": None, "sid": None, "username": None, "colour": None},
            },
            "moves": {"A": [], "B": []},
            "status": g.status,
            "winner": getattr(g, "result", None),
            "connections": set()
        }

        # populate players saved in DB
        for p in getattr(g, "player", []):
            slot = p.player_slot if p.player_slot in ("A", "B") else None
            if slot:
                state["players"][slot]["user_id"] = p.user_id
                state["players"][slot]["username"] = p.username
                state["players"][slot]["colour"] = p.colour

        # populate moves (sorted by move_number)
        moves = sorted(getattr(g, "move", []), key=lambda m: (m.move_number or 0))
        for mv in moves:
            slot = mv.player_slot if mv.player_slot in ("A", "B") else None
            if slot:
                state["moves"][slot].append(mv.notation)

        return state
    except Exception:
        return None


def is_checkmate(game_id: str) -> bool:
    """Return True and archive the game if one side has no remaining pieces.

    Banqi checkmate = all enemy pieces captured. We check both the visible
    `board` and the unrevealed `piece_pool` for presence of 'w' or 'b' pieces.
    """
    try:
        game = GAME_STATES[game_id]
        board = game["board"]
        piece_pool = game["piece_pool"]
    except Exception:
        return False

    try:
        white_present = False
        black_present = False

        # Check board squares
        for v in board.values():
            if not isinstance(v, str):
                continue
            if v in ("unknown", "none", ""):
                continue
            if v.startswith("w"):
                white_present = True
            elif v.startswith("b"):
                black_present = True
            if white_present and black_present:
                return False

        # Check piece pool (unrevealed pieces)
        for k, cnt in piece_pool.items():
            if not isinstance(k, str):
                continue
            if not cnt:
                continue
            if k.startswith("w"):
                white_present = True
            elif k.startswith("b"):
                black_present = True
            if white_present and black_present:
                return False

        # Determine winner
        if not white_present and black_present:
            winner = "b"
        elif not black_present and white_present:
            winner = "w"
        else:
            return False

        # mark finished and archive
        GAME_STATES[game_id]["status"] = "Finished"
        GAME_STATES[game_id]["winner"] = winner
        try:
            archive_game_to_db(game_id)
        except Exception:
            pass

        try:
            socketio.emit("game_over", {"game_id": game_id, "winner": winner}, room=game_id) # type: ignore
        except Exception:
            pass

        return True
    except Exception:
        return False

def archive_game_to_db(game_id) -> None:
    """Persist an in-memory game from `GAME_STATES` into the SQLAlchemy DB.

    Uses `app.db` and models from `app.routes.models`. This function is resilient
    to missing games and DB errors; it will remove the in-memory game after
    successful commit.
    """


    if game_id not in GAME_STATES:
        return

    game_state = GAME_STATES[game_id]

    try:
        # Create model instances and set attributes explicitly to avoid
        # unexpected-keyword errors from some type-checkers/environments.
        game = Game()
        game.id = game_id
        game.board = game_state["board"]
        game.piece_pool = game_state["piece_pool"]
        game.player_turn = game_state.get("player_turn", "A")
        game.move_count = game_state.get("move_count", 0)
        game.status = game_state.get("status", "Inactive")
        db.session.add(game)

        # Persist players if they registered a user_id
        for slot in ["A", "B"]:
            p = game_state["players"][slot]
            if p.get("user_id") is None:
                continue

            gp = Player()
            gp.game_id = game_id
            gp.player_slot = slot
            gp.user_id = p.get("user_id")
            gp.username = p.get("username")
            gp.colour = p.get("colour")
            db.session.add(gp)

        # Save move history. Use a sequential move_number across both players
        # (original behaviour). If you prefer pairwise numbering, change here.
        move_number = 1
        for slot in ["A", "B"]:
            for notation in game_state["moves"][slot]:
                mv = Move()
                mv.game_id = game_id
                mv.player_slot = slot
                mv.move_number = move_number
                mv.notation = notation
                db.session.add(mv)
                move_number += 1

        db.session.commit()
        print(f"[ARCHIVED] Game {game_id} saved to database.")

        # Remove from memory only after successful commit
        del GAME_STATES[game_id]

    except Exception as e:
        db.session.rollback()
        print(f"[ARCHIVE-ERROR] Failed to archive game {game_id}: {e}")
        return


@socketio.on("disconnect")
def handle_disconnect() -> None:
    """Handle socket disconnects: remove sid from any game's connections and
    delete finished games with no remaining connections.
    """
    sid = request.sid # type: ignore
    for gid in list(GAME_STATES.keys()):
        gs = GAME_STATES.get(gid)
        if not gs:
            continue
        conns = gs.get("connections") or set()
        if sid in conns:
            try:
                conns.discard(sid)
            except Exception:
                pass
        # clear player slots that reference this sid
        for slot in ("A", "B"):
            p = gs.get("players", {}).get(slot)
            if p and p.get("sid") == sid:
                p["sid"] = None

        # if no more connected clients and game is finished, free memory
        if (not conns) and gs.get("status") == "Finished":
            try:
                del GAME_STATES[gid]
            except KeyError:
                pass
