from flask import Blueprint, render_template
from .game_socket import active_games

spectate_bp = Blueprint('spectate', __name__, url_prefix='/spectate')

@spectate_bp.route('/', methods=['GET'])
def spectate():
    """List up to 10 active games for spectating.

    Each entry contains: game_id and a simple players string.
    Renders `searching.html` with `active_games` context.
    """
    results = []
    try:
        for game_id, game in list(active_games.items())[:10]:
            try:
                a = game.state.get('players', {}).get('A', {}).get('username')
                b = game.state.get('players', {}).get('B', {}).get('username')
            except Exception:
                a = None
                b = None
            players = f"{a or 'Waiting'} vs {b or 'Waiting'}"
            results.append({
                'game_id': game_id,
                'players': players,
            })
    except Exception:
        results = []

    return render_template('spectate.html', active_games=results)
