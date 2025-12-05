const socket = io({
    withCredentials: true
});  // connects to ws://localhost:5000
let piece_selected = null;  // stores square of 1st click
let square_selected = null;   // stores piece name of 1st click
let img_selected = null;
// let move_mark = null;
let player_turn = 'A';
let player_a_colour = "";
let player_b_colour = "";
let current_player = "u";
let move_count = 0;

//calls upon initialisation.
socket.on("connect", () => {
    socket.emit("join_game", {game_id: GAME_ID});
});

socket.on("joined_game", (data) => {

    // NOW initialize board
    render_board(data.board);
});


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
    if (current_player === "w"){
        current_player = "b";
        turn = document.getElementById("player-a-turn");
        turn.style.colour = "dark-grey";
    }
    else if (current_player === "b"){
        current_player = "w";
        turn = document.getElementById("player-a-turn");
        turn.style.colour = "red";
    }
}
// on piece_onclick, perform a two-click-confirmation moves. Then, process the user's move.
function piece_onclick(img){
    const piece = img.dataset.piece;
    const square = img.dataset.square;
    //if piece_selected, else
    if (piece_selected){
        //case piece_to_select is valid
        if (validate_selected_piece(piece)){
            //If selected_piece is own piece
            if (piece_selected === "unknown"){
                // Case Double Click Unknown Piece
                if (piece === "unknown" && square_selected === square){
                    socket.emit("reveal_piece",{
                        game_id: GAME_ID, square: square,
                    }, (result) =>{
                        if (result.validity === true){
                            reveal_piece({square: square, piece: result.piece});
                        }
                    });
                    clear_selected();
                    // alternate_current_player(); Runs within piece_revealed, as socket is asynchronic.
                }
                // Case unknown and !unknown
                else{
                    clear_selected();
                    assign_selected(img);
                }
            }
            else if (square_selected === square){
                clear_selected();
            }
            else{
                // Case selecting between own_piece or unknown piece.
                clear_selected();
                assign_selected(img);
            }
        }
        else if (piece === "none"){
            // Piece moving to square.
            if (piece_selected === "unknown"){
            }
            else if (isAdjacent(square_selected, square)){
                socket.emit("make_move",
                    {
                        "game_id": GAME_ID,
                        "square1": square_selected,
                        "square2": square,
                        "piece": piece_selected
                    }, (result) => {
                    if (result.validity === true){
                        move({
                        "square1": result.square1,
                        "square2": result.square2,
                        "piece": result.piece
                        });
                    }
                })
            }
            clear_selected();
        }
        else{
            // Try Capture.
            socket.emit("capture",{
            game_id: GAME_ID,
            square1: square_selected,
            square2: square,
            piece1: piece_selected,
            piece2: piece }, (result) => {
                if (result.validity === true){
                    make_capture({
                        "square1": result.square1,
                        "square2": result.square2,
                        "piece1": result.piece1,
                        "piece2": result.piece2
                    });
                    // alternate_current_player(); runs elsewhere as is_capturable is asynchronic.
                }
                clear_selected();
            });
        }
    }
    else if (validate_selected_piece(piece)){
        // else, try to select.
        assign_selected(img);
    }
}

function fetch_game(game_id){
    socket.emit("fetch_game", {game_id}, (game) => {
        const board = game.board;
        return board;
    });
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
    if (piece.startsWith(current_player) || piece.startsWith('u')){
        return true;
    }
    else{
        return false;
    }
}

function squareToCoord(square) {
    const col = square.charCodeAt(0) - 'a'.charCodeAt(0) + 1;  // 'a'→1, 'b'→2 ... 'h'→8
    const row = parseInt(square[1]);  // '1'→1, '4'→4
    return [col, row];
}
function isAdjacent(sq1, sq2) {
    const [col1, row1] = squareToCoord(sq1);
    const [col2, row2] = squareToCoord(sq2);
    return (Math.abs(col1 - col2) === 1 && row1 === row2 || Math.abs(row1 - row2) === 1 && col1 === col2);
}


// socket listener on piece_revealed, accept data as data{square, piece},
function reveal_piece(data){
    const { square, piece } = data;
    const img = document.querySelector(`img[data-square="${square}"]`);
        if (!img) return;
        
        img.src = `/static/image_folder/${piece}.png`;
        //img.style.border = "1vw solid #686868";
        // move_mark = document.querySelector(`img[data-square="${img}"]`);

        img.dataset.piece = piece;
        
        const piece_notation = getKeyByValue(piece_list, piece);
        if (!piece_notation){
            piece_notation = piece;
        }
        notation = (`${square}=(${piece_notation})`);
        render_move(notation);
        if (current_player === "u"){
            current_player = piece[0];
        }
        alternate_current_player();
}

function make_capture(data){
    const {square1, square2, piece1, piece2 } = data;
    const img1 = document.querySelector(`img[data-square="${square1}"]`);
    const img2 = document.querySelector(`img[data-square="${square2}"]`);
    if (!img1 || !img2) return;
    img2.src = `/static/image_folder/${piece1}.png`;
    img2.dataset.piece = piece1;

    img1.src = `/static/image_folder/empty.png`;
    img1.dataset.piece = "none";
    notation = (`${square1} x ${square2}`);
    render_move(notation);
    alternate_current_player();
};
function move(data){
    const {square1, square2, piece} = data;
    const img1 = document.querySelector(`img[data-square="${square1}"]`);
    const img2 = document.querySelector(`img[data-square="${square2}"]`);
    if (!img1 || !img2) return;
    img2.src = `/static/image_folder/${piece}.png`;
    img2.dataset.piece = piece;

    img1.src = `/static/image_folder/empty.png`;
    img1.dataset.piece = "none";

    notation = (`${square1} - ${square2}`);
    render_move(notation);
    alternate_current_player();
}

function getKeyByValue(object, value) {
    return Object.keys(object).find(key => object[key] === value);
}
const piece_list = {
    bK:'b_king', bA: 'b_advisor', bE: 'b_elephant', bR: 'b_chariot', bH: 'b_horse', bC: 'b_catapult', bP: 'b_pawn',
    rK:'w_king', rA: 'w_advisor', rE: 'w_elephant', rR: 'w_chariot', rH: 'w_horse', rC: 'w_catapult', rP: 'w_pawn'
}