## Project overview

- **Type:** Flask web app using `flask_socketio` for real-time game play and `Flask-SQLAlchemy` (SQLite) for persistence.
- **Entry point:** `main.py` (calls `create_app()` then `socketio.run(app, debug=True, use_reloader=False)`).
- **DB bootstrap:** `create_db.py` uses `app.app_context()` then `db.create_all()` to create `banqi_db.sqlite`.

## Big picture / architecture

- `app/__init__.py` constructs the Flask app, initializes `db` (SQLAlchemy) and `socketio` and registers blueprints from `app/routes`.
- HTTP views & page routing live in `app/routes/views.py`, `home.py`, and `game.py` (blueprints: `main`, `home`, `play`).
- Realtime logic lives in `app/routes/game_socket.py` — this is the single in-memory game service using a global `GAME_STATES` dict and Socket.IO event handlers.
- Persistence: `app/routes/models.py` defines `User`, `Game`, `Player`, `Move`. Games are archived from memory to DB with `archive_game_to_db()` in `game_socket.py`.
- Client assets: `static/js/game.js` (client-side socket interactions), templates in `app/templates` (`game.html`, `home.html`, `base.html`).

## Key integration points & conventions

- Socket event names (server side): `fetch_game`, `move_count`, `reveal_piece`, `make_move`, `capture`, `join_game`.
- Server emits: `render_move` (to update all clients), `joined_game` (sent to joining client SID).
- Room management: server calls `join_room(game_id)` and uses `request.sid` for per-connection responses.
- In-memory state: `GAME_STATES` holds a game's `board`, `piece_pool`, `players`, `moves`, `status`. Treat it as the canonical runtime game state until archived.
- Enum mapping: piece strings map to `PieceType` enum names (exact name matches required). `parse_piece()` relies on exact enum member names (e.g. `"w_king"`).

## How to run locally

- Create DB (one-time):
  - PowerShell: `python .\create_db.py`
- Run server:
  - PowerShell: `python .\main.py`
  - Note: `main.py` runs `socketio.run(..., use_reloader=False)` intentionally to avoid duplicate SocketIO threads.

## Development patterns and important examples

- Add a new socket event: edit `app/routes/game_socket.py`, add a handler decorated with `@socketio.on("event_name")`. Use `emit(..., room=...)` to target rooms or `request.sid` for single client responses.
- Persist additional fields to DB: update `app/routes/models.py` (add columns/relationships) and modify `archive_game_to_db()` to set those fields before `db.session.add(...)`.
- Modify capture rules: edit `CAPTURE_RULES` (in `game_socket.py`) — each key is a `PieceType` attacker and the set contains capturable defender `PieceType`s.
- Board coordinates: squares use strings like `a1`..`h4` and `is_adjacent()` uses `square_to_coord()` for orthogonal checks. Update these helpers when changing board geometry.

## Project-specific quirks to watch for

- `GAME_STATES` is an in-memory global — multiple server processes or restarts will lose games unless archived via `archive_game_to_db()`.
- `flask_login` is imported in places (`current_user`) but there's no visible login setup in the codebase; be cautious when adding auth logic — verify `LoginManager` integration if you rely on `current_user`.
- Static path has a folder named `style folder` (space in name) under `static/` — use correct path quoting where needed.
- `create_game()` currently redirects immediately to `start_game`; second-player waiting / matchmaking is TODO — tests or client code assume immediate redirect.

## Quick code pointers (files to edit for common tasks)

- Add HTTP endpoints / pages: `app/routes/*.py` (blueprints registered in `app/__init__.py`).
- Socket logic and rules: `app/routes/game_socket.py`.
- Game initialization and piece pool: `app/routes/game.py` (`init_pos()`, `init_piece_pool()`, `get_piece()`).
- DB schema: `app/routes/models.py` and `create_db.py` for bootstrapping.
- Client socket interactions: `static/js/game.js` and `app/templates/game.html`.

## Examples from the code

- Emitting a move after recording (current behavior):

  `socketio.emit("render_move", {"game_id": game_id, "notation": notation, "player_turn": player_turn})`

- How a new game is initialized in memory:

  `GAME_STATES[game_id] = init_game_state()` (see `init_game_state()` in `game_socket.py`)

## What to ask the maintainers (useful for future agent iterations)

- Should `GAME_STATES` be moved to a persistent store or in-memory cache (Redis) to support multiple processes? 
- Is there an authentication flow intended (there are `current_user` imports but no LoginManager setup)?
- Any expected client-side contracts (socket event shapes) beyond what's implemented in `static/js/game.js`?

Please review this file for anything I missed or any preferred style/phrasing; I can update the doc to match your conventions.
