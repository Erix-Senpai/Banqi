// static/js/game.js
// Simple pointer-based drag + snap for pieces on a responsive board.
// Assumes pieces are <img class="piece"> inside .board-container
// and that positions is an object mapping square -> {x: 0..1, y: 0..1}.
// You can optionally inject 'positions' from Flask as JSON in the template.

console.log("JS loaded correctly!");

async function sendMove(from, to) {
  const response = await fetch('/play/move_piece',{
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ from: from, to: to })
  });

  const result = await response.json();
  console.log(result);
  console.log("TEST");
}

(function () {
  // === 0) CONFIG ===
  // SNAP_THRESHOLD in percent units (0..100). If distance < threshold, we snap.
  const SNAP_THRESHOLD = 12; // tweak for sensitivity

  // Fallback positions mapping (8 columns a..h, 4 rows 1..4).
  // These are midpoints for each cell in normalized coordinates (0..1).
  // If you pass positions from Flask, that will override this.
  const fallbackPositions = (function makePositions(){
    const files = ['a','b','c','d','e','f','g','h'];
    const fileXs = files.map((_,i)=> (i + 0.5) / 8); // 0.0625, 0.1875, ...
    const ranks = [1,2,3,4];
    const rankYs = [3.5,2.5,1.5,0.5].map(v => v / 4); // inverted so 1 is bottom
    const map = {};
    for (let fi=0; fi<files.length; fi++){
      for (let ri=0; ri<ranks.length; ri++){
        const key = files[fi] + ranks[ri];
        map[key] = { x: fileXs[fi], y: rankYs[ri] };
      }
    }
    return map;
  })();

  // Positions may be injected by Flask as a global var `positions`.
  const positions = (typeof window.positions !== "undefined") ? window.positions : fallbackPositions;

  // === 1) utility helpers ===
  function pctDistance(ax, ay, bx, by) {
    // compute Euclidean distance in percentage coordinate space (0..100)
    const dx = (ax - bx) * 100;
    const dy = (ay - by) * 100;
    return Math.sqrt(dx*dx + dy*dy);
  }

  function nearestSquare(normX, normY) {
    // normX, normY are 0..1
    let best = null;
    let bestDist = Infinity;
    for (const [sq, pos] of Object.entries(positions)) {
      const d = pctDistance(normX, normY, pos.x, pos.y);
      if (d < bestDist) { bestDist = d; best = { sq, pos, dist: d }; }
    }
    return best;
  }

  // Given normalized coords (0..1), write to element style variables
  function setPieceXY(el, normX, normY) {
    el.style.setProperty('--x', normX);
    el.style.setProperty('--y', normY);
  }

  // Convert client (page) coordinates to normalized board coords (0..1)
  function clientToBoardNorm(clientX, clientY, boardEl) {
    const r = boardEl.getBoundingClientRect();
    const x = (clientX - r.left) / r.width;
    const y = (clientY - r.top) / r.height;
    // Clamp 0..1:
    return { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) };
  }

  // === 2) Dragging logic ===
  function makeDraggable(pieceEl) {
    let dragging = false;
    let pointerId = null;

    // store piece's original logical square so we can revert if needed
    let originalSquare = pieceEl.dataset.pos || null;

    // On pointerdown, capture pointer and compute offset
    pieceEl.addEventListener('pointerdown', e => {
      e.preventDefault();
      pieceEl.setPointerCapture(e.pointerId);
      pointerId = e.pointerId;
      dragging = true;
      pieceEl.style.transition = 'none'; // disable transition while dragging
      pieceEl.classList.add('dragging');
    });

    // pointermove on document so we track while pointer leaves piece bounds
    document.addEventListener('pointermove', e => {
      if (!dragging || e.pointerId !== pointerId) return;
      const board = pieceEl.closest('.board-container');
      if (!board) return;
      const norm = clientToBoardNorm(e.clientX, e.clientY, board);
      // place piece at pointer location (center)
      setPieceXY(pieceEl, norm.x, norm.y);
    });

    // On pointerup, snap to nearest square and optionally notify backend
    pieceEl.addEventListener('pointerup', async e => {
      if (!dragging || e.pointerId !== pointerId) return;
      dragging = false;
      pieceEl.releasePointerCapture(pointerId);
      pointerId = null;
      pieceEl.classList.remove('dragging');

      const board = pieceEl.closest('.board-container');
      const norm = clientToBoardNorm(e.clientX, e.clientY, board);
      const nearest = nearestSquare(norm.x, norm.y);

      if (nearest && nearest.dist < SNAP_THRESHOLD) {
        // snap to nearest square
        setPieceXY(pieceEl, nearest.pos.x, nearest.pos.y);
        // update logical position on the element
        const fromSquare = pieceEl.dataset.pos || null;
        const toSquare = nearest.sq;
        pieceEl.dataset.pos = toSquare;

        // add smooth transition for snapping
        pieceEl.style.transition = 'top 0.12s, left 0.12s';

        // optional: notify backend of move
        try {
          const res = await sendMoveToServer(fromSquare, toSquare);
          // handle response (e.g., error: revert)
          if (!res || res.status !== 'ok') {
            // server rejected move → revert
            if (fromSquare) {
              const oldPos = positions[fromSquare];
              setPieceXY(pieceEl, oldPos.x, oldPos.y);
              pieceEl.dataset.pos = fromSquare;
            }
            alert((res && res.message) || 'Move rejected by server');
          }
        } catch (err) {
          console.error("Move send failed", err);
        }
      } else {
        // not close enough → revert to original square
        pieceEl.style.transition = 'top 0.12s, left 0.12s';
        if (originalSquare && positions[originalSquare]) {
          setPieceXY(pieceEl, positions[originalSquare].x, positions[originalSquare].y);
          pieceEl.dataset.pos = originalSquare;
        }
      }
    });

    // Clean up pointer cancel (e.g., pointercancel)
    pieceEl.addEventListener('pointercancel', e => {
      if (!dragging) return;
      dragging = false;
      pieceEl.releasePointerCapture(pointerId);
      pointerId = null;
      pieceEl.classList.remove('dragging');
      // revert position
      const original = pieceEl.dataset.pos;
      if (original && positions[original]) {
        setPieceXY(pieceEl, positions[original].x, positions[original].y);
      }
    });
  }

  // === 3) Send move to Flask backend ===
  // Example endpoint: POST /move_piece with JSON {from: 'a1', to: 'a2'}
  async function sendMoveToServer(fromSquare, toSquare) {
    // If fromSquare is null (e.g., piece newly created), decide how you want server to handle it.
    const payload = { from: fromSquare, to: toSquare };
    const resp = await fetch('/move_piece', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      return { status: 'error', message: `HTTP ${resp.status}` };
    }
    return resp.json(); // expects JSON like {status: "ok", ...}
  }

  // === 4) Initialize all pieces on the board ***
  function initBoard() {
    // set initial CSS positions for each piece from its inline vars or dataset
    const pieces = document.querySelectorAll('.board-container .piece');
    pieces.forEach(p => {
      // if element has data-pos and positions mapping, place it there:
      const posName = p.dataset.pos;
      if (posName && positions[posName]) {
        setPieceXY(p, positions[posName].x, positions[posName].y);
      } else {
        // else, if inline --x/--y exist in style, fine, otherwise default center
        const styleX = parseFloat(getComputedStyle(p).getPropertyValue('--x')) || 0.5;
        const styleY = parseFloat(getComputedStyle(p).getPropertyValue('--y')) || 0.5;
        setPieceXY(p, styleX, styleY);
      }
      makeDraggable(p);
    });
  }

  // Wait DOM loaded
  document.addEventListener('DOMContentLoaded', initBoard);
})();
