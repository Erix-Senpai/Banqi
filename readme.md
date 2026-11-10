# Banqi

Banqi is a browser-based, two-player Banqi game built with Flask and
Flask-SocketIO. The server uses SQLite to store users and archived games.

## Setup

### Requirements

- Python 3.13.x is recommended. The development virtual environment is
  configured for Python 3.13.9; the project does not currently declare a
  broader supported Python-version range.
- `requirements.txt` contains the pinned Python dependencies, including Flask,
  Flask-SocketIO, Flask-SQLAlchemy, and Flask-Login.
- No separate database server is needed; the application uses SQLite.
- The browser loads Socket.IO and some styling/fonts from CDNs, so an internet
  connection is needed for those assets.

### Install and run (Windows PowerShell)

From the project directory:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python .\create_db.py
```
### To start the server (Windows PowerShell)
```
python .\main.py
```

If the Python launcher (`py`) is unavailable, install Python 3.13 and use
`python` in place of `py -3.13` when creating the virtual environment.

### Install and run (macOS/Linux)

From the project directory:

```bash
python3.13 --version
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python create_db.py
```
### To start the server (macOS/Linux)
```
python main.py
```

The database setup command creates the tables used by the application. After
starting the server, open <http://127.0.0.1:5000> in a browser. Stop the
development server with `Ctrl+C`.

## How to play

1. Open the site and choose **Play** in the navigation. You can play as a guest;
   registration and login are optional.
2. Wait for another player to join. If you're hosting locally, open another browser
   from different application (e.g. Chrome, Edge).
3. Now you're ready to play.

## Game rules
1. The game board is an 8-by-4 grid of face-down pieces.
2. On your turn, double-click a face-down piece to reveal it. The first reveal
   assigns the players' piece colours; turns alternate after each action.
3. To move, click one of your revealed pieces, then click an empty square
   directly above, below, left, or right of it.
4. To capture, select one of your pieces and then an opposing piece. The
   capture must follow the game's piece-rank rules. Catapults can capture
   along the same row or column by jumping over exactly one intervening piece.

5. The aim is to capture all of the opposing side's pieces, including pieces
   that have not yet been revealed. Use **Offer Draw** to propose a draw or
   **Resign** to concede. Right-click a selected piece to deselect it.

The exact capture hierarchy follows the Taiwanese rule, and may
differ from other Banqi rule sets. Hierarchy are as follows:

1. King
2. Advisor
3. Catapult
4. Elephant
5. Horse
6. Chariot
7. Pawn

Where higher ranking piece may capture any of the equal or lower ranking piece.
With the exception of:
1. Chariot, whom may capture any of the opposing pieces.
2. Pawn follows the aforementioned rule, but can also capture the king.
3. King may not capture pawn.

References: https://en.wikipedia.org/wiki/Banqi

