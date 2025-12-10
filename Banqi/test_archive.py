from app import create_app, db
from app.routes.game_socket import GAME_STATES, archive_game_to_db


def make_sample_game(game_id: str):
    return {
        "board": {f"{f}{r}": "unknown" for f in "abcdefgh" for r in range(1, 5)},
        "piece_pool": {"w_king": 1, "b_king": 1},
        "player_turn": "A",
        "move_count": 0,
        "players": {
            "A": {"user_id": None, "sid": None, "username": "alice", "colour": "w"},
            "B": {"user_id": None, "sid": None, "username": "bob", "colour": "b"},
        },
        "moves": {"A": ["a1 = (w_king)"], "B": []},
        "status": "Inactive",
        "result": "Drawn",
    }


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # ensure tables exist
        db.create_all()

        gid = "testgame02"
        GAME_STATES[gid] = make_sample_game(gid)

        print("Archiving game...")
        archive_game_to_db(gid)

        # verify saved
        from app.routes.models import Game, Player, Move

        g = db.session.get(Game, gid)
        if g:
            print(f"Found Game row: id={g.id}, status={g.status}, move_count={g.move_count}")
        else:
            print("Game row not found")

        players = db.session.query(Player).filter_by(game_id=gid).all()
        print(f"Player rows saved: {len(players)}")

        moves = db.session.query(Move).filter_by(game_id=gid).all()
        print(f"Move rows saved: {len(moves)}")
