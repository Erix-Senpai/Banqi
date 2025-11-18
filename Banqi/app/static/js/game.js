const socket = io();  // connects to ws://localhost:5000

socket.on("piece_selected", (data) => {
    console.log("Server detects piece was selected:", data.square);
});


async function init_board() {
      // Fetch JSON from Flask backend
      const response = await fetch('/play/initialise');
      const data = await response.json();

      render_board(data);
    }

function render_board(pos){
    const boardDiv = document.getElementById("board");
    
    for (const square in pos)
    {
        const piece = pos[square];
        if (piece === "none") continue;

        const img = document.createElement("img");
        img.src=`/static/image_folder/${piece}.png`;
        img.classList.add("piece");
        img.dataset.square = square;
        img.draggable = true;
        img.dataset.piece = piece;


        img.addEventListener("dblclick", () => {
            if (img.dataset.piece === "unknown") {
                console.log("Double clicked unknown at", square);

                /// img.dataset.piece = revealedPiece;
                socket.emit("reveal_piece", { square: square });
            }
        });
        const {top, left} = compute_p(square);
        img.style.top = top;
        img.style.left=left;
        boardDiv.appendChild(img);
    }


}



function compute_p(square){
    const file = square[0];
    const rank = parseInt(square[1]);

    const file_index = file.charCodeAt(0) - 'a'.charCodeAt(0) + 1; // Compute via character code minus a + 1, such that char code 'a' = 1, 'b' = 2...
    const rank_index = 4 - rank;
    console.log("FILE INDEX:" + {file_index})

    const top = 2.75 + rank_index * 25;
    const left = -11.75 + file_index * 12.5;

    return {
        top: top + "%",
        left: left + "%"
    };
}

socket.on("piece_revealed", (data) => {
    const { square, piece } = data;

    console.log(`Revealed ${square} → ${piece}`);

    // find the image on board
    const img = document.querySelector(`img[data-square="${square}"]`);
    if (!img) return;
    
    img.src = `/static/image_folder/${piece}.png`;

    img.dataset.piece = piece;

});