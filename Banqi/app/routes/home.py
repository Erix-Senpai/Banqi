from flask import Blueprint, render_template, session
from flask_login import current_user
from .. import db
from .models import Game, Player

home_bp = Blueprint('home', __name__, url_prefix='/home')


@home_bp.route('/', methods=['POST', 'GET'])
def home():
    previous_games = []
    is_guest = session.get("is_guest", False)

    if current_user.is_authenticated:
        # Find all Player rows for this user, collect their games
        players = Player.query.filter_by(user_id=current_user.id).order_by(Player.id.desc()).limit(20).all()
        seen = set()
        for p in players:
            game = p.game
            if not game or game.id in seen:
                continue
            seen.add(game.id)

            # Collect both players' info (A and B)
            pa = {"name": None, "elo_p": None}
            pb = {"name": None, "elo_p": None}
            for pl in game.player:
                slot = (pl.player_slot or "").upper()
                if slot == "A":
                    pa["name"] = pl.username
                    pa["elo_p"] = pl.elo_p
                elif slot == "B":
                    pb["name"] = pl.username
                    pb["elo_p"] = pl.elo_p
            # Format opponent display to include both players with elo
            opp_line_a = f"{pa['name'] or '-'} ({pa['elo_p'] if pa['elo_p'] is not None else '-'})"
            opp_line_b = f"{pb['name'] or '-'} ({pb['elo_p'] if pb['elo_p'] is not None else '-'})"
            opponent_display = f"{opp_line_a}<br/>{opp_line_b}"

            date = game.date
            formatted_date = date.strftime("%Y-%m-%d") if date else None
            previous_games.append({
                'game_id': game.id,
                'opponent_username': opponent_display,
                'result': p.result,
                'date': formatted_date,
                'elo_change_display': f"{p.elo_change if p.elo_change is not None else int(0)}"
            })
            

    return render_template('home.html', is_guest=is_guest, previous_games=previous_games)
