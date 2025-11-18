from flask_socketio import emit
from .game import get_piece
from .. import socketio

@socketio.on("reveal_piece")
def reveal_piece(data):
    square = data["square"]
    revealed_piece = get_piece()

    # Send the revealed piece to ONLY this client
    emit("piece_revealed", {
        "square": square,
        "piece": revealed_piece
    })