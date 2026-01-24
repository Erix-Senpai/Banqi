import random
from typing import Dict

BOARD_SIZE = 32

# Base piece names used on the board (without colour prefix)
PIECE_BASES = ["king", "advisor", "elephant", "chariot", "catapult", "horse", "pawn"]
RED = 0
BLACK = 1

HIDDEN = 0
REVEALED = 1


class BanqiZobrist:
    def __init__(self, seed: int = 2026):
        rng = random.Random(seed)

        # table[base_piece][colour][face][square_index]
        self.table: Dict = {}
        for base in PIECE_BASES:
            self.table[base] = {
                RED: {
                    HIDDEN: [rng.getrandbits(64) for _ in range(BOARD_SIZE)],
                    REVEALED: [rng.getrandbits(64) for _ in range(BOARD_SIZE)],
                },
                BLACK: {
                    HIDDEN: [rng.getrandbits(64) for _ in range(BOARD_SIZE)],
                    REVEALED: [rng.getrandbits(64) for _ in range(BOARD_SIZE)],
                },
            }

        # whose turn it is
        self.turn_hash = rng.getrandbits(64)

    def piece_hash(self, piece_str: str, face: int, square_index: int) -> int:
        """Return the zobrist value for a piece string like 'w_king' or 'b_pawn'.

        This function derives the base name and colour from the piece string.
        """
        if not isinstance(piece_str, str):
            raise ValueError("piece_str must be a string like 'w_king'")
        parts = piece_str.split("_", 1)
        if len(parts) != 2:
            raise ValueError("piece_str must be like 'w_king' or 'b_pawn'")
        colour_prefix, base = parts
        base = base.lower()
        colour = RED if colour_prefix.lower() == "w" else BLACK
        if base not in self.table:
            raise KeyError(f"Unknown base piece '{base}'")
        return self.table[base][colour][face][square_index]


zobrist = BanqiZobrist()

# Build a consistent square ordering matching INIT_POS(): a1,a2,a3,a4,b1,...,h4
FILES = "abcdefgh"
RANKS = [1, 2, 3, 4]
SQUARES = [f"{f}{r}" for f in FILES for r in RANKS]
SQUARE_INDEX = {sq: i for i, sq in enumerate(SQUARES)}


def compute_initial_zobrist(game: dict) -> int:
    h = 0
    board = game.get("board", {})

    for sq, idx in SQUARE_INDEX.items():
        val = board.get(sq)
        if not val or not isinstance(val, str):
            continue
        if val in ("unknown", "none", ""):
            continue
        # val expected to be like 'w_king' or 'b_pawn'
        try:
            h ^= zobrist.piece_hash(val, REVEALED, idx)
        except Exception:
            # ignore unknown/invalid values silently
            continue

    # player_turn uses 'A' or 'B' — we keep the original behaviour: XOR turn when it's B
    if game.get("player_turn") == "B":
        h ^= zobrist.turn_hash

    return h


def apply_move_hash(game: dict, piece: str, from_sq: str, to_sq: str) -> None:
    """Update game's zobrist hash for a piece moving from from_sq to to_sq.

    Expects `piece` like 'w_king'. Squares are strings like 'a1'.
    """
    try:
        fi = SQUARE_INDEX[from_sq]
        ti = SQUARE_INDEX[to_sq]
        game["zobrist"] ^= zobrist.piece_hash(piece, REVEALED, fi)
        game["zobrist"] ^= zobrist.piece_hash(piece, REVEALED, ti)
    except Exception:
        return


def apply_remove_hash(game: dict, piece: str, square: str) -> None:
    """Remove (XOR out) a piece at `square` from the game's hash."""
    try:
        si = SQUARE_INDEX[square]
        game["zobrist"] ^= zobrist.piece_hash(piece, REVEALED, si)
    except Exception:
        return


def apply_reveal_hash(game: dict, piece: str, square: str) -> None:
    """Update hash when a piece from the pool is revealed onto the board."""
    try:
        si = SQUARE_INDEX[square]
        # pool pieces were not previously hashed on the board; just xor in the revealed piece
        game["zobrist"] ^= zobrist.piece_hash(piece, REVEALED, si)
    except Exception:
        return


def toggle_turn_hash(game: dict) -> None:
    try:
        game["zobrist"] ^= zobrist.turn_hash
    except Exception:
        return


def reset_position_count(game: dict) -> None:
    """Reset position_count. Called when board state changes fundamentally (reveal/capture)."""
    try:
        game["position_count"] = {game.get("zobrist"): 1}
    except Exception:
        pass


def record_position(game: dict) -> bool:
    """Increment the position_count for the current zobrist and return the new count.

    If the count reaches 3, also set game['status'] = 'FINISHED'.
    """
    try:
        current = game.get("zobrist")
        if "position_count" not in game or game["position_count"] is None:
            game["position_count"] = {}
        cnt = game["position_count"].get(current, 0) + 1
        game["position_count"][current] = cnt
        if cnt >= 3:
            return True
        return False
    except Exception:
        return False