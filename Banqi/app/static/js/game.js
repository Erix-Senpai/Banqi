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

