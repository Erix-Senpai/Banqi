from flask_socketio import emit, join_room, leave_room
from .game import get_piece
from .. import socketio
from enum import Enum, auto
from ..routes.game import init_pos, init_piece_pool
from flask import request
from flask_login import current_user
import uuid
import time
from sqlalchemy.orm import selectinload
from flask import current_app, session
import random
from app import db
from .models import Game, Player, Move

PENDING_DISCONNECTED_USER = {}
PENDING_GAME_STATES = {}
LOCKED_GAME_STATES = {}
GAME_STATES = {}
piece_notation_list = {
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
player_turn_toggle = {'A': 'B', 'B': 'A'}
### Socket Event Handlers ###

### Socket Events for Game State ###
@socketio.on("fetch_game")
def fetch_game(game_id: str):
    return GAME_STATES.get(game_id)    

global counter
counter = 0
def create_new_game() -> str:
    global counter
    counter += 1
    rand_uuid = str(uuid.uuid4())[:12]
    game_id = str(rand_uuid + str(counter))  # e.g. "a93b1c2d8ef012", where counter ensures uniqueness
    LOCKED_GAME_STATES[game_id] = init_game_state()
    return game_id

def queue_game(game_id: str, user_id: str, sid: str, username: str) -> None:
    ### Queued game must always be locked.
    game = LOCKED_GAME_STATES[game_id]
    try:
        game.setdefault("connections", set()).add(sid)
    except Exception:
        game["connections"] = set([sid])
    # --- ASSIGN PLAYER SLOT ---
    if game["players"]["A"].get("user_id") is None:
        game["players"]["A"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
    elif game["players"]["B"].get("user_id") is None:
        game["players"]["B"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}


#TODO: Separate Spectators with a different URL/Handler to distinguish from players. Should replace game_status with an enumerator.
@socketio.on("join_game")
def join_game(data: dict) -> None:
    """Handle player joining a game with matchmaking logic.
    
    Flow:
    1. If game_id provided: use that game (from URL)
    2. If no game_id: look for pending game, or redirect to create_game
    3. When 2nd player joins a PENDING game, move it to GAME_STATES and set status="Active"
    """
    # --- MATCHMAKING: If no game_id, find or create pending game ---
    # remember what the client originally sent so we can redirect if needed
    game_id = data.get("game_id")
    
    # Determine user_id and username
    try:
        user_id = session["user_id"]
        username = session["username"]
    except Exception:
        if current_user.is_authenticated:
            session["user_id"] = current_user.id
            session["username"] = current_user.username
            session["is_guest"] = False
        else:
            if "user_id" not in session:
                session["user_id"] = str(uuid.uuid4())[:8]

                session["username"] = f"ANON_{str(uuid.uuid4())[:4]}{random.randint(1000,9999)}"
                session["is_guest"] = True
        user_id = session["user_id"]
        username = session["username"]
    sid = request.sid  # type: ignore
    # --- MATCHMAKING: If no game_id, find or create pending game ---
    if not game_id:
        if not PENDING_GAME_STATES:
            # No pending games; redirect client to create_game
            game_id = create_new_game() # On create game, we immediately create a locked game.
        else:
            # Reserve a pending game id without creating a long-lived iterator.
            # Use popitem() (O(1)) to get a key/value pair and reinsert it
            # immediately to preserve the pending state.
            try:
                game_id, popped_game = PENDING_GAME_STATES.popitem()
                LOCKED_GAME_STATES[game_id] = popped_game
            except KeyError:
                game_id = create_new_game()
            # since the client arrived without a URL, instruct them to navigate
            # to the canonical game URL so their browser shows the game id.

        queue_game(game_id, user_id, sid, username)
        socketio.emit("redirect_to_game", {
            "url": f"/play/game/{game_id}"
        }, room=sid)  # type: ignore
        
        game = LOCKED_GAME_STATES[game_id]
        if game["players"]["A"].get("user_id") and game["players"]["B"].get("user_id"):
            GAME_STATES[game_id] = game
        else:
            PENDING_GAME_STATES[game_id] = game
        return
        # let the client navigate and reconnect to join properly
        
    # --- LOAD GAME STATE ---
    if game_id not in GAME_STATES and game_id not in PENDING_GAME_STATES and game_id not in LOCKED_GAME_STATES:
        # Try to load archived game from DB
        loaded = load_game_from_db(game_id)
        if loaded:
            GAME_STATES[game_id] = loaded
        else:
            game_id = create_new_game()
            queue_game(game_id, user_id, sid, username)
            socketio.emit("redirect_to_game", {
                "url": f"/play/game/{game_id}"
            }, room=sid)  # type: ignore
            game = LOCKED_GAME_STATES[game_id]
            if game["players"]["A"].get("user_id") and game["players"]["B"].get("user_id"):
                GAME_STATES[game_id] = game
            else:
                PENDING_GAME_STATES[game_id] = game
            return
            # Game not found anywhere
    # --- DETERMINE WHICH DICT THE GAME IS IN ---
    game = None
    is_pending = False
    for _ in range(3):
        if game_id in PENDING_GAME_STATES:
            game = PENDING_GAME_STATES[game_id]
            is_pending = True
            break
        elif game_id in LOCKED_GAME_STATES:
            game = LOCKED_GAME_STATES[game_id]
            is_pending = True
            break
        elif game_id in GAME_STATES:
            game = GAME_STATES[game_id]
            break
        else:
            game = None
            socketio.sleep(0.5) #type: ignore
    
    if (not game):
        socketio.emit("error", {"message": "Game not found."}, room=sid)  # type: ignore
        return
    # Join the room
    join_room(game_id)
    try:
        game.setdefault("connections", set()).add(sid)
    except Exception:
        game["connections"] = set([sid])

    # --- ASSIGN PLAYER SLOT ---
    is_player = False
    try:
        if (game["players"]["A"]["user_id"] == user_id):
            game["players"]["A"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
            player_slot = "A"
            is_player = True
        elif (game["players"]["B"]["user_id"] == user_id):
            game["players"]["B"] = {"user_id": user_id, "sid": sid, "username": username, "colour": None}
            player_slot = "B"
            is_player = True
        else:
            player_slot = None
    except Exception:
        leave_room(game_id)
        return

    # --- CHECK IF WE SHOULD MOVE FROM PENDING TO ACTIVE ---
    

    player_turn = game.get("player_turn")
    # Send current state to joining client only
    socketio.emit("joined_game", {
        "game_id": game_id,
        "board": game.get("board"),
        "moves": game.get("moves"),
        "status": game.get("status"),
        "players": game.get("players"),
        "player_slot": player_slot,
        "player_turn": player_turn,
        "is_player": is_player,
        "current_player_colour": game["players"][player_turn]["colour"]
    }, to=request.sid)  # type: ignore

    if is_pending and game["status"] == "Starting" and game["players"]["A"].get("user_id") and game["players"]["B"].get("user_id"):
        # Both players have joined; move to GAME_STATES and activate
        game["status"] = "Ongoing"
        GAME_STATES[game_id] = game
        socketio.emit("game_ready", {
            "game_id": game_id,
            "message": "Both players joined! Game starting."
        }, room=game_id)  # type: ignore
    username_a = game["players"]["A"]["username"]
    username_b = game["players"]["B"]["username"]
    socketio.emit("render_nameplate", {"username_a": username_a, "username_b": username_b}, room=game_id)  # type: ignore




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
        print("archieved game to db.")
    except Exception:
        # keep handler resilient; callers can check `game_archived` or logs
        return

### Socket Events for Player Actions ###
@socketio.on("try_reveal_piece")
def try_reveal_piece(data:dict) -> None:
    try:
        game_id = data["game_id"]
        square = data["square"]

        game = GAME_STATES[game_id]
        current_player_colour = game["player_turn"]
        sid = request.sid  # type: ignore
        # Validate player
        if not(current_user.is_authenticated):
            if (game["players"][current_player_colour]["sid"] != sid) : return
        else:
            if (game["players"][current_player_colour]["user_id"] != current_user.id) : return
        if (game["status"] == "Finished"): return

        # Validate board state
        if not (game["board"][square] == "unknown"): return

        # Validated; reveal piece and update board.
        revealed_piece = get_piece(game["piece_pool"])

        # If colour is not set i.e. on first move, assign colour
        if not game["players"]["A"]["colour"]:
            set_player_colour(game_id, revealed_piece[0])
            game["status"] = "Ongoing"
        
        # Update Board
        game["board"][square] = revealed_piece
        # Get notation using updated piece_notation_list
        notation = (f"{square} = ({piece_notation_list.get(revealed_piece)})")
        # debug
        record_move(game_id, notation)
        socketio.emit("reveal_piece", {"square": square, "piece": revealed_piece}, room=game_id) #type: ignore
    except Exception:
        return


@socketio.on("try_make_move")
def try_make_move(data: dict) -> None:
    try:
        game_id = data["game_id"]
        sq1 = data["square1"]
        sq2 = data["square2"]

        game = GAME_STATES[game_id]
        board = game["board"]
        player_turn = game["player_turn"]

        piece = board[sq1]
        sid = request.sid  # type: ignore
        # Validate player
        if (game["players"][player_turn]["sid"] != sid): return
        if (game["status"] == "Finished"): return
        player_colour = game["players"][player_turn]["colour"]
        # Validate board state
        if not (board[sq1][0] == player_colour and board[sq2] == "none" and is_adjacent(sq1, sq2)): return

        # Validated; make_move and update board.
        board[sq1] = "none"
        board[sq2] = piece
        notation = (f"{sq1} - {sq2}")
        record_move(game_id, notation)
        socketio.emit("make_move",{"square1": sq1, "square2": sq2, "piece": piece}, room=game_id) #type: ignore
    except Exception:
        return

@socketio.on("try_capture")
def try_capture(data: dict) -> None:
    try:
        game_id = data["game_id"]
        sq1 = data["square1"]
        sq2 = data["square2"]

        game = GAME_STATES[game_id]
        board = game["board"]
        player_turn = game["player_turn"]
        p1 = board[sq1]
        p2 = board[sq2]
        
        sid = request.sid  # type: ignore
        # Validate player
        if (game["players"][player_turn]["sid"] != sid): return
        if (game["status"] == "Finished"): return
        player_colour = game["players"][player_turn]["colour"]
        # Validate board state
        if not (board[sq1][0] == player_colour):
            return
        # Validate if is_capturable
        if not (capturable(sq1, sq2, p1, p2, board)):
            return
        # Validated; make_capture and update board.
        board[sq1] = "none"
        board[sq2] = p1
        notation = (f"{sq1} x {sq2}")
        record_move(game_id, notation)
        socketio.emit("make_capture",{"square1": sq1, "square2": sq2, "piece1": p1, "piece2": p2}, room=game_id) #type: ignore
    except Exception:
        return

@socketio.on("disconnected")
def handle_disconnect(data) -> None:
    """Handle socket disconnects: remove sid from any game's connections and
    delete finished games with no remaining connections.
    Note, does not handle disconnects for non-logged in user, immediately considers as forfeited.
    """
    try:
        if not (data):
            return
        game_id = data.get("game_id")
        if game_id in PENDING_GAME_STATES:
            del PENDING_GAME_STATES[game_id]
            return
        if game_id in LOCKED_GAME_STATES:
            del LOCKED_GAME_STATES[game_id]
            return
        
        game = GAME_STATES[game_id]
        if (game["status"] != "Ongoing"): return
        sid = request.sid # type: ignore
        user_id = session["user_id"]
        username = session["username"]
        
        PENDING_DISCONNECTED_USER[user_id] = {
            "deadline": time.time() + 15,  # 15 seconds from now
            "game_id": game_id,
            "Loser": username
        }
    except Exception:
        return

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

def disconnect_watcher(app):
    with app.app_context():
        while True:
            now = time.time()
            for user_id, data in list(PENDING_DISCONNECTED_USER.items()):
                if now >= data["deadline"]:
                    game_id = data["game_id"]
                    loser = data["Loser"]
                    try:
                        checkmate_by_disconnection(game_id, loser)
                    except Exception as e:
                        print(f"[DISCONNECT-WATCHER-ERROR] checkmate_by_disconnection failed: {e}")
                    try:
                        del PENDING_DISCONNECTED_USER[user_id]
                    except KeyError:
                        pass
            socketio.sleep(5)

# Note: do NOT start the disconnect watcher at import time. The SocketIO
# server is initialized in the app factory (`socketio.init_app(app)`), so the
# background task must be started after initialization. The app factory will
# call `socketio.start_background_task(game_socket.disconnect_watcher)`.
@socketio.on("try_draw")
def try_draw(data: dict) -> None:
    try:
        game_id = data["game_id"]
        game = GAME_STATES[game_id]

        if (game["status"] != "Ongoing"): return
        sid = request.sid  # type: ignore
        user_id = current_user.id if current_user.is_authenticated else None
        # Validate player

        player_a = game["players"]["A"]
        player_b = game["players"]["B"]
        
        if (player_a["sid"] == sid or player_a["user_id"] == user_id):
            draw_offer = "A"
            # Bypass checker for spam.
            if player_a["req"] == "draw": return
            player_a["req"] = "draw"
        elif (player_b["sid"] == sid or player_b["user_id"] == user_id):
            draw_offer = "B"
            # Bypass checker for spam.
            if player_b["req"] == "draw": return
            player_b["req"] = "draw"
        else:
            return
        if (is_draw(game_id)):
            return
        # Identify opponent slot and sid
        opponent_slot = player_turn_toggle[draw_offer]
        opponent = game["players"].get(opponent_slot, {})
        opponent_sid = opponent.get("sid")

        socketio.emit("draw_request", to=opponent_sid)  # type: ignore
    except Exception:
        return


def draw_toggle(game_id: str) -> None:
    players = GAME_STATES[game_id]['players']
    players["A"]["req"] = None
    players["B"]["req"] = None

def is_draw(game_id: str) -> bool:
    game = GAME_STATES[game_id]
    player_a = game["players"]["A"]
    player_b = game["players"]["B"]
    if (player_a["req"] == "draw" and player_b["req"] == "draw"):
            # End the game as a draw
            game["status"] = "Finished"
            # Use a neutral 'Draw' marker for winner field so client shows appropriately
            game["winner"] = "Draw"
            socketio.emit("game_over", {"game_id": game_id, "winner": None, "result": "Draw", "reason": "Draw Agreement"}, room=game_id)  # type: ignore
            archive_game_to_db(game_id)
            return True
    return False

@socketio.on("respond_draw")
def respond_draw(data: dict) -> None:
    """Handle opponent's response to a draw request.

    Expects `{"game_id": ..., "accept": bool}`. If accepted the game is
    finished as a draw and archived; if declined, notify the offering player.
    """
    try:
        game_id = str(data.get("game_id"))
        accept = bool(data.get("accept"))
        decline = bool(data.get("decline"))
        game = GAME_STATES[game_id]
        sid = request.sid  # type: ignore
        user_id = current_user.id if current_user.is_authenticated else None

        # Determine which slot is responding
        if (game["players"]["A"]["sid"] == sid or game["players"]["A"]["user_id"] == user_id):
            responder = "A"
        elif (game["players"]["B"]["sid"] == sid or game["players"]["B"]["user_id"] == user_id):
            responder = "B"
        else:
            return

        # Find the offering player (the other slot)
        offerer = player_turn_toggle[responder]
        offerer_sid = game["players"][offerer].get("sid")

        if accept:
            game["players"][responder]["req"] = "draw"
            is_draw(game_id)
            return
            # End the game as a draw
        elif decline:
            draw_toggle(game_id)
            # Notify offerer that draw was declined
            if offerer_sid:
                socketio.emit("draw_declined", {"game_id": game_id, "by": responder}, to=offerer_sid)  # type: ignore

    except Exception:
        return

@socketio.on("try_resign")
def try_resign(data: dict) -> None:
    try:
        game_id = data["game_id"]
        game = GAME_STATES[game_id]

        if (game["status"] != "Ongoing"): return

        sid = request.sid  # type: ignore
        user_id = current_user.id if current_user.is_authenticated else None
        # Validate player
        if (game["players"]["A"]["sid"] == sid or game["players"]["A"]["user_id"] == user_id):
            resignation_player = "A"
            winner_team = "B"
        elif (game["players"]["B"]["sid"] == sid or game["players"]["B"]["user_id"] == user_id):
            resignation_player = "B"
            winner_team = "A"
        else:
            return
        

        # Validated; resign the game.
        winner = game["players"][winner_team]["username"]
        game["status"] = "Finished"
        game["winner"] = winner
        archive_game_to_db(game_id)
        # mark finished and archive
        socketio.emit("game_over", {"game_id": game_id, "winner": winner, "result": "win", "reason": "Resignation"}, room=game_id) # type: ignore
    except Exception:
        return
    
### Game Logic Functions ###


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

def record_move(game_id: str, notation: str)->None:
    game = GAME_STATES[game_id]
    turn = game["player_turn"]
    game["moves"][turn].append(notation)
    game["player_turn"] = player_turn_toggle[turn]
    game["move_count"] += 1
    is_checkmate(game_id)
    draw_toggle(game_id)


def set_player_colour(game_id: str, colour_a :str) -> None:
    GAME_STATES[game_id]["players"]["A"]["colour"] = colour_a
    if (colour_a == "w"):
        GAME_STATES[game_id]["players"]["B"]["colour"] = "b"
    else:
        GAME_STATES[game_id]["players"]["B"]["colour"] = "w"


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
            winner_team = "b"
        elif not black_present and white_present:
            winner_team = "w"
        else:
            return False

        # mark finished and archive
        if (game["players"]["A"]["colour"] == winner_team):
            winner = game["players"]["A"]["username"]
        else:
            winner = game["players"]["B"]["username"]
        GAME_STATES[game_id]["status"] = "Finished"
        GAME_STATES[game_id]["winner"] = winner
        try:
            archive_game_to_db(game_id)
        except Exception:
            pass

        try:
            socketio.emit("game_over", {"game_id": game_id, "winner": winner, "result": "win", "reason": "Checkmate"}, room=game_id) # type: ignore
        except Exception:
            pass

        return True
    except Exception:
        return False

def checkmate_by_disconnection(game_id: str, loser_username: str) -> None:
    """Handle checkmate due to player disconnection."""
    try:
        game = GAME_STATES.get(game_id)
        if not game or game.get("status") != "Ongoing":
            return

        game["status"] = "Finished"
        if (game["players"]["A"]["username"] == loser_username):
            winner_username = game["players"]["B"]["username"]
        else:
            winner_username = game["players"]["A"]["username"]
        game["winner"] = winner_username
        # Emit to connected clients first so the message is delivered
        # even if archiving later removes the in-memory state.
        try:
            socketio.emit("game_over", {"game_id": game_id, "winner": winner_username, "reason": "Abandonment."}, room=game_id) # type: ignore
        except Exception as e:
            print(f"[DISCONNECT-EMIT-ERROR] Failed to emit game_over for {game_id}: {e}")
        # Archive the game; keep this resilient to DB errors.
        try:
            archive_game_to_db(game_id)
        except Exception as e:
            print(f"[DISCONNECT-ARCHIVE-ERROR] Failed to archive {game_id}: {e}")
    except Exception:
        return

def can_capture(attacker: PieceType, defender: PieceType) -> bool:
    return defender in CAPTURE_RULES.get(attacker, set())

def parse_piece(piece_str: str) -> PieceType:
    return PieceType[piece_str]

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
        "status": "Starting",
        "winner": None,
        # runtime-only: track connected socket ids (not persisted)
        "connections": set()
    }

### Database handling for archiving/restoring games ###

# Board Schema:
# - Game: id (str, PK), board (JSON), piece_pool (JSON), player_turn (str),
#         move_count (int), status (str), result (str)
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
                "A": {"user_id": None, "sid": None, "username": None, "colour": None, "req": None},
                "B": {"user_id": None, "sid": None, "username": None, "colour": None, "req": None},
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
        current_app.logger.exception(f"Failed to load game {game_id}")
        return None

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

        # Remove from memory only after successful commit
        del GAME_STATES[game_id]

    except Exception as e:
        db.session.rollback()
        print(f"[ARCHIVE-ERROR] Failed to archive game {game_id}: {e}")
        return
