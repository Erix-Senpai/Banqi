const socket = io();  // connects to ws://localhost:5000
let piece_selected = null;  // stores square of 1st click
let square_selected = null;   // stores piece name of 1st click
let img_selected = null;
let player_turn = 'A';
let player_a_colour = "";
let player_b_colour = "";
let current_player = "u";
let move_count = 0;
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
        img.addEventListener("contextmenu",(event) => {
            event.preventDefault();
            piece_onrightclick();
        });

        const {top, left} = compute_pos(square);    //compute_pos to get the position of square{top,left} displayed on UI. Apply styling to piece.
        img.style.top = top;
        img.style.left=left;
        boardDiv.appendChild(img);
    }
}
function render_move(notations){
    notation = String(notations)
    const p = document.createElement("p");
    p.textContent = notation;
    console.debug(`current player turn: ${player_turn}`);
    if (player_turn === 'A'){

        const notationDiv = document.getElementById("move-notation-one");
        notationDiv.appendChild(p);

        const m = document.createElement("p");
        move_count += 1;
        m.textContent = move_count;
        const movenumberDiv = document.getElementById("move-number");
        movenumberDiv.appendChild(m);

        player_turn = 'B';
    }
    else if (player_turn === 'B'){
        const notationDiv = document.getElementById("move-notation-two");
        notationDiv.appendChild(p);
        player_turn = 'A';
    }
}

// On right click, de-select.
function piece_onrightclick(){
    clear_selected();
};
function clear_selected(){
    try{
        square_selected = null;
        piece_selected = null;
        img_selected.style.removeProperty("border");
    }
    catch (error){
        return;
    }
    
}
function assign_selected(img){
    piece_selected = img.dataset.piece;
    square_selected = img.dataset.square;
    img_selected = img;
    img.style.border = "0.2vw solid #e3d89ae6";
}
function alternate_current_player(){
    console.debug(`alternate_current_player triggered`);
    console.debug(`current alternate_current_player: ${current_player}`);
    if (current_player === "w"){
        current_player = "b";
        console.debug(`CURRENT PLAYER: switched from w to ${current_player}.`);
        turn = document.getElementById("player-a-turn");
        turn.style.colour = "dark-grey";
    }
    else if (current_player === "b"){
        current_player = "w";
        console.debug(`CURRENT PLAYER: switched from b to ${current_player}`);
        turn = document.getElementById("player-a-turn");
        turn.style.colour = "red";
    }
    else{
        console.debug(`error. current_player === ${current_player}`);
    }
}
// on piece_onclick, perform a two-click-confirmation moves. Then, process the user's move.
function piece_onclick(img){
    const piece = img.dataset.piece;
    const square = img.dataset.square;
    console.debug(`vvvvvvvvvvvv`);
    console.debug(`piece_selected: ${piece_selected}`);
    console.debug(`piece currently clicked: ${piece}`);
    console.debug(`current_player: ${current_player}`);

    console.debug(`^^^^^^^^^^^^`);
    //if piece_selected, else
    if (piece_selected){
        //case piece_to_select is valid
        if (validate_selected_piece(piece)){
            //If selected_piece is own piece
            if (piece_selected === "unknown"){
                // Case Double Click Unknown Piece
                if (piece === "unknown" && square_selected === square){
                    socket.emit("reveal_piece", { square: square });
                    console.debug(`current player has yet to switch. preparing to switch.`);
                    clear_selected();
                    // alternate_current_player(); Runs within piece_revealed, as socket is asynchronic.
                    console.debug(`current player has switched to ${current_player}`);
                }
                // Case unknown and !unknown
                else{
                    clear_selected();
                    assign_selected(img);
                }
            }
            else{
                // Case selecting between own_piece or unknown piece.
                clear_selected();
                assign_selected(img);
            }
        }
        else{
            // Try Capture, as piece_selected and 2nd piece is enemy piece.
            socket.emit("is_capturable",{
            square1: square_selected,
            square2: square,
            piece1: piece_selected,
            piece2: piece }, (result) => {
                if (result){
                    make_capture({
                        "square1": square_selected,
                        "square2": square,
                        "piece1": piece_selected,
                        "piece2": piece
                    });
                    // alternate_current_player(); runs elsewhere as is_capturable is asynchronic.
                }
                clear_selected();
            })
        }
    }
    else if (validate_selected_piece(piece)){
        // else, try to select.
        console.debug(`No piece Selected. Selecting ${piece}.`);
        assign_selected(img);
    }
}

function init_team(colour){
    socket.emit("Player_A", { colour: colour});
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

function validate_selected_piece(piece){
    console.debug(`Comparing...`);
    console.debug(`${piece} startswith ${current_player}?`);
    if (piece.startsWith(current_player) || piece.startsWith('u')){
        console.debug(`true`);
        return true;
    }
    else{
        return false;
    }
}

// socket listener on piece_revealed, accept data as data{square, piece}, 
socket.on("piece_revealed", (data) => {
    const { square, piece } = data;
    const img = document.querySelector(`img[data-square="${square}"]`);
        if (!img) return;
        
        img.src = `/static/image_folder/${piece}.png`;

        img.dataset.piece = piece;
        console.debug(`SQUARE: ${square}, PIECE:${piece}`);
        
        const piece_notation = getKeyByValue(piece_list, piece);
        if (!piece_notation){
            piece_notation = piece;
        }
        notation = (`${square}=(${piece_notation})`);
        console.debug(`SQUARE: ${square}, PIECE:${piece_notation}`);
        render_move(notation);
    if (!player_a_colour){
        console.debug(`comparing piece.startswith: ${piece}, w_?`);
        if (piece.startsWith("w_")){
            console.debug(`true!`);
            player_a_colour = "w";
            player_b_colour = "b";
            current_player = "w";
        }
        else{
            console.debug(`false!`);
            current_player = "b";
            player_a_colour = "b";
            player_b_colour = "w";
        }
    }
    alternate_current_player();
});

function make_capture(data){
    const {square1, square2, piece1, piece2 } = data;
    console.log(`RECEIVED SQUARES AND PIECES: square1:${square1}, square2:${square2}, piece1:${piece1}, piece2:${piece2}`);
    const img1 = document.querySelector(`img[data-square="${square1}"]`);
    const img2 = document.querySelector(`img[data-square="${square2}"]`);
    if (!img1 || !img2) return;
    console.log("replacing...");
    img2.src = `/static/image_folder/${piece1}.png`;
    img2.dataset.piece = piece1;

    img1.remove();
    img1.removeAttribute("data-piece");

    notation = (`${square1} x ${square2}`);
    render_move(notation);
    alternate_current_player();
};

function getKeyByValue(object, value) {
    return Object.keys(object).find(key => object[key] === value);
}
const piece_list = {
    bK:'b_king', bA: 'b_advisor', bE: 'b_elephant', bR: 'b_chariot', bH: 'b_horse', bC: 'b_catapult', bP: 'b_pawn',
    rK:'w_king', rA: 'w_advisor', rE: 'w_elephant', rR: 'w_chariot', rH: 'w_horse', rC: 'w_catapult', rP: 'w_pawn'
}

/* Debug:

socket.on("piece_selected", (data) => {
    console.log("Server detects piece was selected:", data.square);
});

*/