from flask_socketio import emit, join_room, leave_room
from .. import socketio
from enum import Enum, auto
from .game_helper import INIT_POS, INIT_PIECE_POOL, get_piece
from flask import request
from flask_login import current_user
import uuid
from sqlalchemy.orm import selectinload
from flask import current_app, session
import random
from app import db
from .models import Game, Player, Move
import threading
import time
from datetime import date
from collections import deque
class Game_result(Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
class Game_State:
    def __init__(self, game_id, is_private=False):
        self.id = game_id
        self.lock = threading.Lock()

        self.state = init_game_state()
        self.is_private = is_private

        self.created_at = time.time()
        self.started_at = time.time()

        # runtime-only (NOT in state dict)
        self.sockets = {}      # user_id -> sid
        self.spectators = {}   # user_id -> sid
active_games: dict[str, Game_State]
active_games = {}
open_games: deque[str] = deque()
queue_lock = threading.Lock()
pending_disconnected_user = {}
online_users = {}
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
### Socket Event Handlers ###

@socketio.on("connect")
def connect():
    """Handle new socket connection: track online users."""
    sid = request.sid  # type: ignore
    username = session.get("username")
    guest = session.get("is_guest")
    user_id = session.get("user_id")
    online_users[user_id] = {"username": username, "guest": guest, "sid": sid}


def create_game(is_private=False):
    game_id = str(uuid.uuid4())[:8]
    game = Game_State(game_id, is_private=is_private)
    active_games[game_id] = game
    open_games.append(game.id)
    return game_id, game

def queue_game(game_id, user_id, username):
    try:
        game = active_games.get(game_id)
        if not game:
            return
        players = game.state.get("players")
        if not players:
            return
        if game.state["status"] == GAME_STATE.STARTING.name:
            if players["A"].get("user_id") != user_id and players["B"].get("user_id") != user_id:
                if (players["A"].get("user_id") == None):
                    players["A"]["user_id"] = user_id
                    players["A"]["username"] = username
                elif (players["B"].get("user_id") == None):
                    players["B"]["user_id"] = user_id
                    players["B"]["username"] = username
                if game.state["players"]["A"].get("user_id") != None and game.state["players"]["B"].get("user_id") != None:
                    game.state["status"] = GAME_STATE.ONGOING.name
                    if not game.is_private:
                        open_games.remove(game.id)
                
    except Exception:
        pass

#TODO: When a user opens a game through database, the game is not processed correctly.
@socketio.on("join_game")
def join_game(data: dict) -> None:
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
                session["user_id"] = f"ANON_{str(uuid.uuid4())[:8]}"
                session["username"] = f"ANON_{str(uuid.uuid4())[:4]}{random.randint(1000,9999)}"
                session["is_guest"] = True
        user_id = session["user_id"]
        username = session["username"]
    sid = request.sid  # type: ignore
    game_id = data.get("game_id")
    is_private = data.get("is_private") or False
    if not game_id:
        with queue_lock:
            if open_games:
                game_id = open_games.popleft()
                game = active_games.get(game_id)
                if not game:
                    game_id, game = create_game(is_private)
            else:
                game_id, game = create_game(is_private)
        
        with game.lock:
            queue_game(game_id, user_id, username)
        socketio.emit("redirect_to_game", {
            "url": f"/play/game/{game_id}"
            }, room=sid)  # type: ignore
        return
    else:
        game = active_games.get(game_id)
        if not game:
            ### if game_id is provided, but not found, try search through db.
            loaded = load_game_from_db(game_id)
            if loaded:
                try:
                    print("debugging...")
                    game = Game_State(game_id)
                    game.state = loaded
                    active_games[game_id] = game
                    print("game loaded.")
                    game = active_games.get(game_id)
                    print(f"Active game with id {game_id} : {active_games.get(game_id)}  ")
                    view_game_history(game_id, user_id)
                except Exception as e:
                    print(f"debug exception. {e}")
                    return
                return
            else:
                game_id, game = create_game(is_private)
                with game.lock:
                    queue_game(game_id, user_id, username)
                socketio.emit("redirect_to_game", {
                    "url": f"/play/game/{game_id}"
                    }, room=sid)  # type: ignore
                return
    if not game:
        socketio.emit("error", {"message": "Game not found."}, room=sid)  # type: ignore
        return

    ### Game_id hold true here on
    # Discern if player is trying to join a game, or simply redirected.
    if game.is_private:
        try:
            queue_game(game_id, user_id, username)
        except Exception:
            socketio.emit("error", {"message": "Game not found."}, room=sid)  # type: ignore
            return
    join_room(game_id)
    if game.state["status"] == GAME_STATE.ONGOING.name:
        socketio.emit("game_ready", {
            "game_id": game_id,
            "message": "Both players joined! Game starting."
        }, room=game_id)  # type: ignore
    if game.state["players"]["A"].get("user_id") == user_id and game.state["status"] != GAME_STATE.FINISHED.name:
        player_slot = "A"
        is_player = True
    elif game.state["players"]["B"].get("user_id") == user_id and game.state["status"] != GAME_STATE.FINISHED.name:
        player_slot = "B"
        is_player = True
    else:
        player_slot = "Spectator"
        is_player = False

    current_player_turn = game.state.get("player_turn")
    socketio.emit("joined_game", {
        "game_id": game_id,
        "board": game.state.get("board"),
        "moves": game.state.get("moves"),
        "status": game.state.get("status"),
        "players": game.state.get("players"),
        "player_slot": player_slot,
        "player_turn": current_player_turn,
        "is_player": is_player,
        "current_player_colour": game.state["players"][current_player_turn]["colour"]
    }, to=request.sid)  # type: ignore
    username_a = game.state["players"]["A"]["username"]
    username_b = game.state["players"]["B"]["username"]
    socketio.emit("render_nameplate", {"username_a": username_a, "username_b": username_b, "is_player": is_player}, room=game_id)  # type: ignore
    

def view_game_history(game_id: str, user_id: str) -> None:
    print("debugging...")
    sid = request.sid # type: ignore
    game = active_games.get(game_id)
    if not game:
        return
    player_slot = None
    current_player_turn = game.state.get("player_turn")
    is_player = False
    socketio.emit("joined_game", {
        "game_id": game_id,
        "board": game.state.get("board"),
        "moves": game.state.get("moves"),
        "status": game.state.get("status"),
        "players": game.state.get("players"),
        "player_slot": player_slot,
        "player_turn": current_player_turn,
        "is_player": is_player,
        "current_player_colour": game.state["players"][current_player_turn]["colour"]
    }, to=request.sid)  # type: ignore
    username_a = game.state["players"]["A"]["username"]
    username_b = game.state["players"]["B"]["username"]
    socketio.emit("render_nameplate", {"username_a": username_a, "username_b": username_b, "is_player": is_player}, room=sid)  # type: ignore
#TODO:  
### Socket Events for Player Actions ###
@socketio.on("try_reveal_piece")
def try_reveal_piece(data:dict) -> None:
    """
    data receives for {"game_id":..., "square":...}, validates the user and move validity, and attempts to reveal a piece from the pool onto the board. Returns None.
    """
    try:
        game_id = data["game_id"]
        square = data["square"]
        game = active_games.get(game_id)
        if not game:
            raise Exception
        current_player_colour = game.state["player_turn"]
        user_id = session["user_id"]
        # Validate player
        if (game.state["players"][current_player_colour]["user_id"] != user_id): return
        if (game.state["status"] == GAME_STATE.FINISHED.name): return

        # Validate board state
        if not (game.state["board"][square] == "unknown"): return

        # Validated; reveal piece and update board.
        revealed_piece = get_piece(game.state["piece_pool"])

        # If colour is not set i.e. on first move, assign colour
        if not game.state["players"]["A"]["colour"]:
            set_player_colour(game_id, revealed_piece[0])
            game.state["status"] = GAME_STATE.ONGOING.name
        
        # Update Board
        game.state["board"][square] = revealed_piece
        # update zobrist for reveal and reset position count (board state changed)
        try:
            apply_reveal_hash(game.state, revealed_piece, square)
            reset_position_count(game.state)
        except Exception:
            pass
        # Get notation using updated piece_notation_list
        notation = (f"{square} = ({PIECE_NOTATION_LIST.get(revealed_piece)})")
        socketio.emit("reveal_piece", {"square": square, "piece": revealed_piece}, room=game_id) #type: ignore
        record_move(game_id, notation)
    except Exception:
        return


@socketio.on("try_make_move")
def try_make_move(data: dict) -> None:
    """
    data receives for {"game_id":..., "square1":..., "square2":...}, validates the user and move validity, and attempts to make a move on the board. Returns None.
    """
    try:
        game_id = data["game_id"]
        sq1 = data["square1"]
        sq2 = data["square2"]
        game = active_games.get(game_id)
        if not game:
            raise Exception
        board = game.state["board"]
        player_turn = game.state["player_turn"]

        piece = board[sq1]
        user_id = session["user_id"]
        # Validate player
        if (game.state["players"][player_turn]["user_id"] != user_id): return
        if (game.state["status"] != GAME_STATE.ONGOING.name): return
        player_colour = game.state["players"][player_turn]["colour"]
        # Validate board state
        if not (board[sq1][0] == player_colour and board[sq2] == "none" and is_adjacent(sq1, sq2)): return

        # Validated; make_move and update board.
        board[sq1] = "none"
        board[sq2] = piece
        # update zobrist for move
        try:
            apply_move_hash(game.state, piece, sq1, sq2)
        except Exception:
            pass
        notation = (f"{sq1} - {sq2}")
        
        socketio.emit("make_move",{"square1": sq1, "square2": sq2, "piece": piece}, room=game_id) #type: ignore
        record_move(game_id, notation)
    except Exception:
        return

@socketio.on("try_capture")
def try_capture(data: dict) -> None:
    """
    data receives for {"game_id":..., "square1":..., "square2":...}, validates the user and move validity, and attempts to make a capture on the board. Returns None.
    """
    try:
        game_id = data["game_id"]
        sq1 = data["square1"]
        sq2 = data["square2"]
        game = active_games.get(game_id)
        if not game:
            raise Exception
        board = game.state["board"]
        player_turn = game.state["player_turn"]
        p1 = board[sq1]
        p2 = board[sq2]
        
        # Validate player
        if (game.state["players"][player_turn]["user_id"] != session["user_id"]): return
        if (game.state["status"] != GAME_STATE.ONGOING.name): return
        player_colour = game.state["players"][player_turn]["colour"]
        # Validate board state
        if not (board[sq1][0] == player_colour):
            return
        # Validate if is_capturable
        if not (capturable(sq1, sq2, p1, p2, board)):
            return
        # Validated; make_capture and update board.
        board[sq1] = "none"
        board[sq2] = p1
        # update zobrist for capture: remove captured piece and move attacker, then reset position count
        try:
            apply_remove_hash(game.state, p2, sq2)
            apply_move_hash(game.state, p1, sq1, sq2)
            reset_position_count(game.state)
        except Exception:
            pass
        notation = (f"{sq1} x {sq2}")
        
        socketio.emit("make_capture",{"square1": sq1, "square2": sq2, "piece1": p1, "piece2": p2}, room=game_id) #type: ignore
        record_move(game_id, notation)
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
        game = active_games.get(game_id)
        if not game:
            return
        if (game.state["status"] == GAME_STATE.FINISHED.name): return
        with game.lock:
            if game.state["status"] == GAME_STATE.STARTING.name:
                del active_games[game_id]
                del game.state[game_id]
                return
        sid = request.sid # type: ignore
        user_id = session["user_id"]
        username = session["username"]
        try:
            online_users.pop(user_id, None)
        except KeyError:
            pass
        pending_disconnected_user[user_id] = {
            "deadline": time.time() + 15,  # 15 seconds from now
            "game_id": game_id,
            "Loser": username
        }
    except Exception:
        return

    for gid in list(game.state.keys()):
        gs = game.state.get(gid)
        if not gs:
            continue
        try:
            conns = gs.get("connections") or set()
        except Exception:
            conns = set()
        if sid in conns:
            try:
                conns.discard(sid)
            except Exception:
                pass
        # clear player slots that reference this sid
        for slot in ("A", "B"):
            try:
                p = gs.get("players", {}).get(slot)
                if p and p.get("sid") == sid:
                    p["sid"] = None
            except Exception:
                return

        # if no more connected clients and game is finished, free memory
        if (not conns) and gs.get("status") == GAME_STATE.FINISHED.name:
            try:
                del game.state[gid]
                del active_games[gid]
            except KeyError:
                pass

def disconnect_watcher(app):
    with app.app_context():
        while True:
            now = time.time()
            for user_id, data in list(pending_disconnected_user.items()):
                if now >= data["deadline"]:
                    game_id = data["game_id"]
                    loser = data["Loser"]
                    try:
                        checkmate_by_disconnection(game_id, loser)
                    except Exception as e:
                        print(f"[DISCONNECT-WATCHER-ERROR] checkmate_by_disconnection failed: {e}")
                    try:
                        del pending_disconnected_user[user_id]
                    except KeyError:
                        pass
            socketio.sleep(5)

@socketio.on("try_draw")
def try_draw(data: dict) -> None:
    """
    Handle a player's request to offer a draw to their opponent.
    """
    try:
        game_id = data["game_id"]
        game = active_games.get(game_id)
        if not game:
            return

        if (game.state["status"] != GAME_STATE.ONGOING.name): return
        user_id = session["user_id"]
        # Validate player

        player_a = game.state["players"]["A"]
        player_b = game.state["players"]["B"]
        
        if (player_a["user_id"] == user_id):
            draw_offer = "A"
            # Bypass checker for spam.
            if player_a["req"] == "draw": return
            player_a["req"] = "draw"
        elif (player_b["user_id"] == user_id):
            draw_offer = "B"
            # Bypass checker for spam.
            if player_b["req"] == "draw": return
            player_b["req"] = "draw"
        else:
            return
        if (is_draw(game_id)):
            return
        # Identify opponent slot and sid
        opponent_slot = PLAYER_TURN_TOGGLE[draw_offer]
        opponent_user_id = game.state["players"][opponent_slot]["user_id"]
        try:
            opponent_sid = online_users[opponent_user_id].get("sid")
        except KeyError:
            return

        socketio.emit("draw_request", to=opponent_sid)  # type: ignore
    except Exception:
        return


def draw_toggle(game_id: str) -> None:
    """
    Toggle the draw request status for both players in a game.

    :param game_id: The ID of the game.
    :type game_id: str
    """
    game = active_games.get(game_id)
    if not game:
        return
    players = game.state["players"]
    players["A"]["req"] = None
    players["B"]["req"] = None

def is_draw(game_id: str) -> bool:
    """
    Check if both players have requested a draw.

    :param game_id: The ID of the game.
    :type game_id: str
    :return: True if both players have requested a draw, False otherwise.
    :rtype: bool
    """
    game = active_games.get(game_id)
    if not game:
        return False
    player_a = game.state["players"]["A"]
    player_b = game.state["players"]["B"]
    if (player_a["req"] == "draw" and player_b["req"] == "draw"):
            # End the game as a draw
            game.state["status"] = GAME_STATE.FINISHED.name
            # Use a neutral 'Draw' marker for winner field so client shows appropriately
            game.state["winner"] = None
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

        game = active_games.get(game_id)
        if not game:
            return
        user_id = session["user_id"]

        # Determine which slot is responding
        if (game.state["players"]["A"]["user_id"] == user_id):
            responder = "A"
        elif (game.state["players"]["B"]["user_id"] == user_id):
            responder = "B"
        else:
            return
        

        if accept:
            game.state["players"][responder]["req"] = "draw"
            is_draw(game_id)
            return
            # End the game as a draw
        elif decline:
            draw_toggle(game_id)

            offerer = PLAYER_TURN_TOGGLE[responder]
            offerer_user_id = game.state["players"][offerer]["user_id"]
            try:
                offerer_sid = online_users[offerer_user_id].get("sid")
            except KeyError:
                return
            # Notify offerer that draw was declined
            if offerer_sid:
                socketio.emit("draw_declined", {"game_id": game_id, "by": responder}, to=offerer_sid)  # type: ignore

    except Exception:
        return

@socketio.on("try_resign")
def try_resign(data: dict) -> None:
    """
    Docstring for try_resign.
    User Tries to resign from the game. Validates user and game state, then marks the game as finished with the opponent as the winner.
    :param data: Description
    :type data: dict
    """
    try:
        game_id = data["game_id"]
        game = active_games.get(game_id)
        if not game:
            return

        if (game.state["status"] != GAME_STATE.ONGOING.name): return

        user_id = session["user_id"]
        
        # Validate player
        if (game.state["players"]["A"]["user_id"] == user_id):
            winner_team = "B"
        elif (game.state["players"]["B"]["user_id"] == user_id):
            winner_team = "A"
        else:
            return
        

        # Validated; resign the game.
        winner = game.state["players"][winner_team]["username"]
        game.state["status"] = GAME_STATE.FINISHED.name
        game.state["winner"] = winner
        archive_game_to_db(game_id)
        # mark finished and archive
        socketio.emit("game_over", {"game_id": game_id, "winner": winner, "result": "win", "reason": "Resignation"}, room=game_id) # type: ignore
    except Exception:
        return
    
### Game Logic Functions ###

class GAME_STATE(Enum):
    STARTING = auto()
    ONGOING = auto()
    FINISHED = auto()

class PieceType(Enum):
    """
    Docstring for PieceType
    Enumeration of piece types and piece capture rules.
    """
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
    """
    Docstring for record_move
    Records the move notation into the game state, updates turn and move count, checks for game end conditions (draw by repetition or checkmate), and emits relevant events.

    :param game_id: Description
    :type game_id: str
    :param notation: Description
    :type notation: str
    """
    game = active_games.get(game_id)
    if not game:
        return
    turn = game.state["player_turn"]
    game.state["moves"][turn].append(notation)
    game.state["player_turn"] = PLAYER_TURN_TOGGLE[turn]
    game.state["move_count"] += 1
    # toggle zobrist turn hash and update repetition counts
    try:
        toggle_turn_hash(game.state)
        if (record_position(game.state)):
            game.state["status"] = GAME_STATE.FINISHED.name
            socketio.emit("game_over", {"game_id": game_id, "winner": None, "result": "Draw", "reason": "draw by repetition"}, room=game_id) # type: ignore
            try:
                archive_game_to_db(game_id)
                return
            except Exception:
                pass
        elif (is_checkmate(game_id)):
            try:
                game.state["status"] = GAME_STATE.FINISHED.name
                winner = game.state["winner"]
                socketio.emit("game_over", {"game_id": game_id, "winner": winner, "result": "win", "reason": "checkmate"}, room=game_id) # type: ignore
                archive_game_to_db(game_id)
                return
            except Exception:
                pass
    except Exception:
        pass
    
    draw_toggle(game_id)


def set_player_colour(game_id: str, colour_a :str) -> None:
    """
    Docstring for set_player_colour
    On first piece reveal, assign player colours based on revealed piece colour.

    :param game_id: Description
    :type game_id: str
    :param colour_a: Description
    :type colour_a: str
    """
    game = active_games.get(game_id)
    if not game:
        return
    game.state["players"]["A"]["colour"] = colour_a
    if (colour_a == "w"):
        game.state["players"]["B"]["colour"] = "b"
    else:
        game.state["players"]["B"]["colour"] = "w"


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
    Also checks for repeated moves (draw condition).
    """
    try:
        game = active_games.get(game_id)
        if not game:
            return False
        board = game.state["board"]
        piece_pool = game.state["piece_pool"]
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
        if (game.state["players"]["A"]["colour"] == winner_team):
            winner = game.state["players"]["A"]["username"]
        else:
            winner = game.state["players"]["B"]["username"]
        game.state["winner"] = winner

        return True
    except Exception:
        return False

def checkmate_by_disconnection(game_id: str, loser_username: str) -> None:
    """Handle checkmate due to player disconnection."""
    try:
        game = active_games.get(game_id)
        if not game:
            return
        if game.state.get("status") != GAME_STATE.ONGOING.name:
            return

        game.state["status"] = GAME_STATE.FINISHED.name
        if (game.state["players"]["A"]["username"] == loser_username):
            winner_username = game.state["players"]["B"]["username"]
        else:
            winner_username = game.state["players"]["A"]["username"]
        game.state["winner"] = winner_username
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

from .zobrist_repetition import (
    compute_initial_zobrist,
    apply_reveal_hash,
    apply_move_hash,
    apply_remove_hash,
    toggle_turn_hash,
    record_position,
    reset_position_count,
)



def init_game_state():
    state = {
        "board": INIT_POS(),
        "piece_pool": INIT_PIECE_POOL(),
        "player_turn": "A",
        "move_count": 0,
        "players": {
            "A": {"user_id": None,  "username": None, "colour": None},
            "B": {"user_id": None, "username": None, "colour": None}
        },
        "moves": {
            "A": [],
            "B": []
        },
        "status": GAME_STATE.STARTING.name,
        "winner": None,
        # runtime-only: track connected socket ids (not persisted)
    }
    state["zobrist"] = compute_initial_zobrist(state)
    state["position_count"] = {state["zobrist"]: 1}
    return state

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
            "winner": getattr(g, "result", None)
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

        # ensure zobrist and position_count are present for in-memory play
        try:
            state["zobrist"] = compute_initial_zobrist(state)
            state["position_count"] = {state["zobrist"]: 1}
        except Exception:
            state["zobrist"] = 0
            state["position_count"] = {}
        return state
    except Exception:
        current_app.logger.exception(f"Failed to load game {game_id}")
        return None
def archive_game_to_db(game_id) -> None:
    game = active_games.get(game_id)
    if not game:
        return

    game_state = game.state

    try:
        game_model = Game()
        game_model.id = game_id
        game_model.board = game_state["board"]
        game_model.piece_pool = game_state["piece_pool"]
        game_model.player_turn = game_state.get("player_turn", "A")
        game_model.move_count = game_state.get("move_count", 0)
        game_model.status = GAME_STATE.FINISHED.name
        game_model.date = date.today()

        db.session.add(game_model)

        winner_slot = game_state.get("winner")  # "A", "B", or None

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

            # ✅ assign per-player result
            if winner_slot is None:
                gp.result = Game_result.DRAW.name
            elif slot == winner_slot:
                gp.result = Game_result.WIN.name
            else:
                gp.result = Game_result.LOSS.name

            db.session.add(gp)

        # moves unchanged
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

        del active_games[game_id]

    except Exception as e:
        db.session.rollback()
        print(f"[ARCHIVE-ERROR] Failed to archive game {game_id}: {e}")

