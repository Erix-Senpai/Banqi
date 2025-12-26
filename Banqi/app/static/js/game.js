const socket = io({
    withCredentials: true
});  // connects to ws://localhost:5000
let piece_selected = null;  // stores square of 1st click
let square_selected = null;   // stores piece name of 1st click
let img_selected = null;
// let move_mark = null;

// Initialise by default.
let player_turn = 'A';
let player_slot = null;
let current_player_colour = null;
let game_status = "Starting";

//calls upon initialisation.
socket.on("connect", () => {
    // GAME_ID can be empty string if user clicked "Play" without a URL game_id
    // The join_game handler will manage matchmaking
    socket.emit("join_game", {game_id: GAME_ID || null});
});


socket.on("redirect_to_create", (data) => {
    // No pending games available; redirect to create_game
    window.location.href = data.url;
});


socket.on("redirect_to_game", (data) => {
    // Server instructs client to navigate to canonical game URL
    if (data && data.url) {
        window.location.href = data.url;
    }
});

socket.on("game_ready", (data) => {
    game_status = "Ongoing";
    console.debug("Player Slot:", player_slot);
    if (player_slot === "B"){
        username_a = data.username_b;
        username_b = data.username_a;
    }
    else{
        username_a = data.username_a;
        username_b = data.username_b;
    }
    console.debug("username_a:",username_a, "(You)");
    console.debug("username_b", username_b);
    render_nameplate(username_a, username_b);
    console.debug("game Status updated to Ongoing.")
});

socket.on("error", (data) => {
    // Game not found
    alert("Error: " + data.message);
    window.location.href = "/";
});

socket.on("joined_game", (data) => {

    // NOW initialize board
    render_board(data.board);
    console.debug("test");

    render_move_history(
        data.moves["A"] || [],
        data.moves["B"] || []
    );
    console.debug("successfully rendered move history.");

    // Initialise board data. Differs for different user.
    player_turn = data.player_turn; // A or B.
    player_slot = data.player_slot; // A or B, or None / Spectator.
    current_player_colour = data.current_player_colour; // w or b, nullable.
    game_status = data.status; // Starting / Ongoing / Finished.

    console.debug("player_turn:" + player_turn);
    console.debug("player_slot:" + player_slot);
    console.debug("current_player_colour:" + current_player_colour);
    console.debug("game_status:" + game_status);
});

socket.on("game_over", (data) => {
    const winner = data.winner;
    alert(`Game Over! Winner: ${winner}`);

    game_status = "Finished";
    new_game_link = document.getElementById("new_game");
    new_game_link.setAttribute("type","button");
    new_game_link.innerHTML = `<a class="nav-item nav-link" href="/play/game">New Game</a>`;
});

// Incoming draw request from opponent: prompt user to accept/decline
socket.on("draw_request", (data) => {
    // data: {game_id, from, from_username}
    if (game_status !== "Ongoing") return;

    const draw_btn = document.getElementById("draw-btn");
    const draw_offer_decline = document.getElementById("draw-offer-decline");
    
    if (!draw_offer_decline)
    {
        const aA = document.createElement("a");
        aA.textContent = "❌";
        aA.className = "draw-offer";
        aA.id = "draw-offer-decline";
        aA.setAttribute("type", "button");

        const aB = document.createElement("a");
        aB.textContent = "✔";
        aB.className = "draw-offer";
        aB.id = "draw-offer-accept";
        aB.setAttribute("type", "button");

        draw_btn.appendChild(aA);
        draw_btn.appendChild(aB);

    }
    //<a class="draw-offer" id="draw-offer-decline" type="button">❌</a>
    // <a class="draw-offer" id="draw-offer-accept" type="button">✔</a>
});

document.addEventListener("DOMContentLoaded", () => {
    const draw_decine_btn = document.getElementById("draw-offer-decline");

    if (draw_decine_btn) {
        draw_decine_btn.addEventListener("click", handleDrawDecline);
    }
});

function handleDrawDecline(){
    const draw_offer_decline = document.getElementById("draw-offer-decline");
    const draw_offer_accept = document.getElementById("draw-offer-accept");
    if (draw_offer_decline && draw_offer_accept){
        draw_offer_decline.remove();
        draw_offer_accept.remove();
    }

    socket.emit("respond_draw", {game_id: GAME_ID, accept: "decline"});
}


document.addEventListener("DOMContentLoaded", () => {
    const draw_accept_btn = document.getElementById("draw-offer-accept");

    if (draw_accept_btn) {
        draw_accept_btn.addEventListener("click", handleDrawAccept);
    }
});

function handleDrawAccept(){
    draw_btn_reply();
    socket.emit("respond_draw", {game_id: GAME_ID, accept: "accept"});
}
function draw_btn_reply(){
    const draw_offer_decline = document.getElementById("draw-offer-decline");
    const draw_offer_accept = document.getElementById("draw-offer-accept");
    if (draw_offer_decline && draw_offer_accept){
        draw_offer_decline.remove();
        draw_offer_accept.remove();
    }
}

socket.on("draw_offered", (data) => {
    // notify offerer that the request was sent
    if (data && data.game_id === GAME_ID){
        const draw_btn = document.getElementById("draw-btn");
        const aA = document.createElement("a");
        aA.textContent.remove();
        aA.textContent = "Draw Offered.";
        aA.className = "draw-offer";
        aA.id = "draw-offer-display-btn";
        aA.setAttribute("type", "button");
        draw_btn.appendChild(aA);
    }
});

socket.on("draw_declined", (data) => {
    // notify the offerer that opponent declined
    if (data && data.game_id === GAME_ID){
        if (game_status !== "Ongoing")
        {
            return;
        }
        else {
            const draw_btn = document.getElementById("draw-btn");
            const aA = document.createElement("a");
            aA.textContent = "Offer Declined.";
            aA.className = "draw-offer";
            aA.id = "draw-offer-display-btn";
            aA.setAttribute("type", "button");
            draw_btn.appendChild(aA);

        }
    }
});
document.addEventListener("DOMContentLoaded", () => {
    const draw_offer_display_btn = document.getElementById("draw-offer-display-btn");

    if (draw_offer_display_btn) {
        draw_offer_display_btn.addEventListener("click", ()=>{
            draw_offer_display_btn.remove();
        });
    }
});


document.addEventListener("DOMContentLoaded", () => {
    const resignBtn = document.getElementById("resign-btn");

    if (resignBtn) {
        resignBtn.addEventListener("click", handleResign);
    }
});

function handleResign() {
    if (game_status != "Ongoing"){
        return;
    }
    if (!confirm("Are you sure you want to resign?")){
        return;
    }
    socket.emit("try_resign", {game_id: GAME_ID});
    return;
}
// socket listener on 'board_state', accept data as pos{square: piece, ...}, then call render_board(pos)


// Handle Draw Button
document.addEventListener("DOMContentLoaded", () => {
    const draw_btn = document.getElementById("draw-btn");
    if (draw_btn) {
        draw_btn.addEventListener("click", ()=> handleDrawOffer());
    }
});


function handleDrawOffer() {
    const draw_btn = document.getElementById("draw-btn");
    if (game_status != "Ongoing"){
        return;
    }
    if (draw_btn.textContent === "Draw Offered" || draw_btn.textContent !== "Offer Draw"){
        return;
    }
    draw_btn.textContent = "Draw offered";
    draw_btn.ariaDisabled = true;
    console.debug(String(draw_btn.textContent));

    socket.emit("try_draw", {game_id: GAME_ID});
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
            if (game_status === "Finished") return;
            piece_onclick(img);
        });
        img.addEventListener("contextmenu",(event) => {
            if (game_status === "Finished") return;
            event.preventDefault();
            piece_onrightclick();
        });

        const {top, left} = compute_pos(square);    //compute_pos to get the position of square{top,left} displayed on UI. Apply styling to piece.
        img.style.top = top;
        img.style.left=left;
        boardDiv.appendChild(img);
    }
}

function render_nameplate(username_a, username_b){
    const player_a = document.getElementById("player_a");
    const player_b = document.getElementById("player_b");

    player_a.setAttribute("type", "button");
    player_a.innerHTML = `<a class="username-item username-link" href="/user/${username_a}">${username_a} (You)</a>`;

    player_b.setAttribute("type", "button");
    player_b.innerHTML = `<a class="username-item username-link" href="/user/${username_b}">${username_b}</a>`;
};

let moveCount = 0;

function render_move(notationA = null, notationB = null) {
    const container = document.getElementById("move-list");

    // Player A move → start a new turn
    if (notationA && notationA !== "none") {
        moveCount++;

        const movCol = document.createElement("div");
        movCol.className = "mov-col";

        // Move number
        const moveNum = document.createElement("p");
        moveNum.textContent = `${moveCount}.`;

        // Player A move
        const pA = document.createElement("p");
        pA.textContent = notationA;

        // Placeholder for Player B (optional but keeps layout stable)
        const pB = document.createElement("p");
        pB.textContent = "";

        movCol.appendChild(moveNum);
        movCol.appendChild(pA);
        movCol.appendChild(pB);

        container.appendChild(movCol);
    }

    // Player B move → fill last turn
    if (notationB && notationB !== "none") {
        const lastTurn = container.lastElementChild;
        if (!lastTurn) return;

        const pTags = lastTurn.querySelectorAll("p");
        if (pTags.length >= 3) {
            pTags[2].textContent = notationB;
        }
    }

    draw_btn_reply();
}

function render_move_history(movesA = [], movesB = []) {
    const container = document.getElementById("move-list");

    // Reset state
    container.innerHTML = "";
    moveCount = 0;

    const maxLen = Math.max(movesA.length, movesB.length);

    for (let i = 0; i < maxLen; i++) {
        const a = movesA[i] ?? null;
        const b = movesB[i] ?? null;

        // Feed into existing logic
        render_move(a, b);
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
function alternate_current_player_colour(){
    if (current_player_colour === "w"){
        current_player_colour = "b";
        turn = document.getElementById("player-a-turn");
    }
    else if (current_player_colour === "b"){
        current_player_colour = "w";
        turn = document.getElementById("player-a-turn");
    }
    if (player_turn === 'A'){

        player_turn = 'B';
    }
    else if (player_turn === 'B'){
        player_turn = 'A';
    }
}
// on piece_onclick, perform a two-click-confirmation moves. Then, process the user's move.
function piece_onclick(img){
    console.debug("player_turn: ", player_turn, "player_slot: ", player_slot);
    if (player_turn !== player_slot){
        return;
    }
    if (game_status !== "Ongoing"){
        return;
    }
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
                    socket.emit("try_reveal_piece",{game_id: GAME_ID, square: square});
                    clear_selected();
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
            console.debug("Attempting to move from", square_selected, "to", square);
            if (piece_selected === "unknown"){
            }
            else if (isAdjacent(square_selected, square)){
                socket.emit("try_make_move",
                    {
                        "game_id": GAME_ID,
                        "square1": square_selected,
                        "square2": square
                    });
            }
            clear_selected();
        }
        else{
            // Try Capture.
            socket.emit("try_capture",{
            game_id: GAME_ID,
            square1: square_selected,
            square2: square});
            clear_selected();
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
    if (piece.startsWith(current_player_colour) || piece.startsWith('u')){
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

socket.on("disconnect", () => {
    console.log("Disconnected from server");
    // note: cannot reliably emit to server from within the 'disconnect' event
    // because the transport is already gone. Use beforeunload to notify server
    // when the user voluntarily closes the page.
});

// Notify server when the page is about to unload so it can mark a pending
// disconnect. This has a better chance of delivering than emitting from
// the socket 'disconnect' handler.
window.addEventListener('beforeunload', (ev) => {
    try {
        socket.emit('disconnected', { game_id: GAME_ID });
    } catch (e) {
        // best-effort; ignore failures
    }
});

// socket listener on piece_revealed, accept data as data{square, piece},
socket.on("reveal_piece", data => {
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
        if (current_player_colour === "u" || current_player_colour === null){
            current_player_colour = piece[0];
        }
        if (player_turn === 'A'){
        render_move(notation, null);
        }
        else if (player_turn === 'B'){
        render_move(null, notation);
        }
    
        alternate_current_player_colour();
});

socket.on("make_capture", data => {
    const {square1, square2, piece1, piece2 } = data;
    const img1 = document.querySelector(`img[data-square="${square1}"]`);
    const img2 = document.querySelector(`img[data-square="${square2}"]`);
    if (!img1 || !img2) return;
    img2.src = `/static/image_folder/${piece1}.png`;
    img2.dataset.piece = piece1;

    img1.src = `/static/image_folder/empty.png`;
    img1.dataset.piece = "none";
    notation = (`${square1} x ${square2}`);
    if (player_turn === 'A'){
        render_move(notation, null);
    }
    else if (player_turn === 'B'){
        render_move(null, notation);
    }
    alternate_current_player_colour();
});
socket.on("make_move", data => {
    const {square1, square2, piece} = data;
    const img1 = document.querySelector(`img[data-square="${square1}"]`);
    const img2 = document.querySelector(`img[data-square="${square2}"]`);
    if (!img1 || !img2) return;
    img2.src = `/static/image_folder/${piece}.png`;
    img2.dataset.piece = piece;

    img1.src = `/static/image_folder/empty.png`;
    img1.dataset.piece = "none";

    notation = (`${square1} - ${square2}`);
    if (player_turn === 'A'){
        render_move(notation, null);
    }
    else if (player_turn === 'B'){
        render_move(null, notation);
    }
    alternate_current_player_colour();
});


function getKeyByValue(object, value) {
    return Object.keys(object).find(key => object[key] === value);
}
const piece_list = {
    bK:'b_king', bA: 'b_advisor', bE: 'b_elephant', bR: 'b_chariot', bH: 'b_horse', bC: 'b_catapult', bP: 'b_pawn',
    rK:'w_king', rA: 'w_advisor', rE: 'w_elephant', rR: 'w_chariot', rH: 'w_horse', rC: 'w_catapult', rP: 'w_pawn'
}