from app import db
from flask_login import UserMixin
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(24), unique=True, nullable = False)
    password_hash = db.Column(db.String(256), nullable = False)

    game = db.relationship("Player", back_populates="user")

class Game(db.Model):
    __tablename__ = "game"

    id = db.Column(db.String(12), primary_key=True, unique=True)

    board = db.Column(db.JSON, nullable=False)
    piece_pool = db.Column(db.JSON, nullable=False)
    player_turn = db.Column(db.String(1), nullable = False, default="A")

    move_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="Inactive")
    winner = db.Column(db.String(32), default=None)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    player = db.relationship("Player", back_populates="game", cascade="all, delete-orphan")
    move = db.relationship("Move", back_populates="game", cascade="all, delete-orphan")


class Player(db.Model):
    __tablename__ = "player"
    id = db.Column(db.Integer, primary_key=True)
    
    game_id = db.Column(db.String(12), db.ForeignKey("game.id"))
    player_slot = db.Column(db.String(1))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    username = db.Column(db.String(64))
    colour = db.Column(db.String(1))

    game = db.relationship("Game", back_populates = "player")
    user = db.relationship("User", back_populates = "game")

class Move(db.Model):
    __tablename__ = "move"
    id = db.Column(db.Integer, primary_key = True)
    
    game_id = db.Column(db.String(12), db.ForeignKey("game.id"))
    player_slot = db.Column(db.String(1))

    move_number = db.Column(db.Integer)
    notation = db.Column(db.String(128))
    
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    game = db.relationship("Game", back_populates="move")
