from app import db
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Game(db.Model):
    __tablename__ = "game"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    player1_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    player2_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    player1_colour = db.Column(db.String(1))  # "w" or "b"
    player2_colour = db.Column(db.String(1))

    board_state = db.Column(db.Text)          # JSON string of all pieces
    game_status = db.Column(db.String(20))    # active / finished / aborted
