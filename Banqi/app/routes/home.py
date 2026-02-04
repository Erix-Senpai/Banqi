from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user
from .. import db
from .models import Game, Player

home_bp = Blueprint('home', __name__, url_prefix='/home')
@home_bp.route('/', methods = ['POST', 'GET'])
def home():
    previous_games = []
    
    if current_user.is_authenticated:
        # Find all Player rows for this user, collect their games
        players = Player.query.filter_by(user_id=current_user.id).order_by(Player.id.desc()).limit(50).all()
        seen = set()
        for p in players:
            game = p.game
            if not game or game.id in seen:
                continue
            seen.add(game.id)

            # Find opponent (other player) username if available
            opponent = None
            for pl in game.player:
                if pl.user_id != current_user.id:
                    opponent = pl.username or None
                    break
            date = game.date
            formatted_date = date.strftime("%Y-%m-%d")
            previous_games.append({
                'game_id': game.id,
                'opponent_username': opponent,
                'result': p.result,
                'date': formatted_date
            })

    return render_template('home.html', previous_games=previous_games)
