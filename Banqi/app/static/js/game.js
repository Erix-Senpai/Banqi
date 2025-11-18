const socket = io();  // connects to ws://localhost:5000
let piece_selected = null;  // stores square of 1st click
let square_selected = null;   // stores piece name of 1st click


// From game.html call to init_board.
async function init_board() {
      const response = await fetch('/play/initialise');     // Fetch pos from game.py as it initialises board data.
      const data = await response.json();

      render_board(data);   // render_board to initialise board with provided data.
      // Can be configured to initialise an existing game.
    }

// render_board by deploying the board statically.
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

        // addEventListener to img, on click, decide if board needs to be updated.
        img.addEventListener("click", () => {
            piece_onclick(img);
        });

        const {top, left} = compute_pos(square);    //compute_pos to get the position of square{top,left} displayed on UI. Apply styling to piece.
        img.style.top = top;
        img.style.left=left;
        boardDiv.appendChild(img);
    }


}

// on piece_onclick, perform a two-click-confirmation moves. Then, process the user's move.
function piece_onclick(img){
    const square = img.dataset.square
    const piece = img.dataset.piece
    if (!square_selected){  // If in Deselected State, select.
        square_selected = square;
        piece_selected = piece;
        img.style.boxShadow = "0 0 10px 4px rgba(227, 216, 154, 1)";
        return;
    }   // Else, Perform calculation.
    else if (square_selected === square && piece==="unknown"){
        console.log("Double clicked unknown at", square);

        /// img.dataset.piece = revealedPiece;
        socket.emit("reveal_piece", { square: square });
    }
    else if(square_selected != square && piece){
        // Perform Capture Calculation.
    }
    img.style.boxShadow = "none";
    square_selected = null;
    piece_selected = null;
    return;
}

// calculate_p to map the board by correctly positioning them to the UI by intaking square{file:str,rank:int}, and returns pos.
function compute_pos(square){
    const file = square[0];
    const rank = parseInt(square[1]);

    const file_index = file.charCodeAt(0) - 'a'.charCodeAt(0) + 1; // Compute via character code minus a + 1, such that char code 'a' = 1, 'b' = 2...
    const rank_index = 4 - rank;

    // Calculate proportional position displayed on html.
    const top = 2.75 + rank_index * 25;
    const left = -11.75 + file_index * 12.5;

    return {top: top + "%", left: left + "%"};
}

// socket listener on piece_revealed, accept data as data{square, piece}, 
socket.on("piece_revealed", (data) => {
    const { square, piece } = data;

    /*debug:
    console.log(`Revealed ${square} → ${piece}`);
    */
    // find the image on board
    const img = document.querySelector(`img[data-square="${square}"]`);
    if (!img) return;
    
    img.src = `/static/image_folder/${piece}.png`;

    img.dataset.piece = piece;

});



/* Debug:

socket.on("piece_selected", (data) => {
    console.log("Server detects piece was selected:", data.square);
});

*/