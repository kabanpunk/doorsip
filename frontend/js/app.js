const API_URL = '/api';
let WS_URL = `ws://${window.location.host}/ws`;

let state = {
    playerId: null,
    roomCode: null,
    isHost: false,
    selectedGameId: null,
    ws: null,
    choiceMade: false,
    currentCardType: null,
    cardFlipped: false
};

// Screen management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');

    if (screenId === 'create-room') {
        loadGames();
    }
}

// Toast notifications
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show' + (isError ? ' error' : '');
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// Load available games
async function loadGames() {
    const container = document.getElementById('games-list');
    container.innerHTML = '<p class="loading">Загрузка игр...</p>';

    try {
        const response = await fetch(`${API_URL}/games/`);
        const games = await response.json();

        if (games.length === 0) {
            container.innerHTML = '<p class="loading">Нет доступных игр. Сначала добавьте игры в базу данных.</p>';
            return;
        }

        container.innerHTML = games.map(game => `
            <div class="game-item" data-id="${game.id}" onclick="selectGame(${game.id})">
                <h4>${game.name}</h4>
                <p>${game.description || 'Без описания'} (${game.cards_count} карт)</p>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<p class="loading">Ошибка загрузки игр</p>';
        console.error('Error loading games:', error);
    }
}

function selectGame(gameId) {
    state.selectedGameId = gameId;
    document.querySelectorAll('.game-item').forEach(item => {
        item.classList.toggle('selected', parseInt(item.dataset.id) === gameId);
    });
}

// Create room
async function createRoom() {
    const nickname = document.getElementById('host-nickname').value.trim();
    if (!nickname) {
        showToast('Введи никнейм', true);
        return;
    }
    if (!state.selectedGameId) {
        showToast('Выбери игру', true);
        return;
    }

    try {
        const response = await fetch(`${API_URL}/rooms/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: state.selectedGameId,
                host_nickname: nickname
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || 'Ошибка создания комнаты', true);
            return;
        }

        const data = await response.json();
        state.playerId = data.player_id;
        state.roomCode = data.room_code;
        state.isHost = true;

        updateLobby(data.room);
        connectWebSocket();
        showScreen('lobby');
    } catch (error) {
        showToast('Ошибка создания комнаты', true);
        console.error(error);
    }
}

// Join room
async function joinRoom() {
    const roomCode = document.getElementById('room-code-input').value.trim().toUpperCase();
    const nickname = document.getElementById('player-nickname').value.trim();

    if (!roomCode) {
        showToast('Введи код комнаты', true);
        return;
    }
    if (!nickname) {
        showToast('Введи никнейм', true);
        return;
    }

    try {
        const response = await fetch(`${API_URL}/rooms/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: roomCode,
                nickname: nickname
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || 'Ошибка входа в комнату', true);
            return;
        }

        const data = await response.json();
        state.playerId = data.player_id;
        state.roomCode = roomCode;
        state.isHost = false;

        updateLobby(data.room);
        showScreen('lobby');

        // Connect and notify others after connection is established
        connectWebSocket(() => {
            state.ws.send(JSON.stringify({
                type: 'player_joined',
                nickname: nickname
            }));
        });
    } catch (error) {
        showToast('Ошибка входа в комнату', true);
        console.error(error);
    }
}

// Update lobby display
function updateLobby(room) {
    document.getElementById('lobby-code').textContent = room.code;
    document.getElementById('lobby-game-name').textContent = room.game_name;

    const playersList = document.getElementById('lobby-players');
    playersList.innerHTML = room.players.map(p => `
        <li>
            ${p.nickname}
            ${p.is_host ? '<span class="host-badge">ХОСТ</span>' : ''}
        </li>
    `).join('');

    document.getElementById('host-controls').classList.toggle('hidden', !state.isHost);
    document.getElementById('waiting-msg').classList.toggle('hidden', state.isHost);
}

// WebSocket connection
function connectWebSocket(onConnected = null) {
    if (state.ws) {
        state.ws.close();
    }

    state.ws = new WebSocket(`${WS_URL}/${state.roomCode}`);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
        if (onConnected) onConnected();
    };

    state.ws.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'player_joined':
            showToast(`${message.nickname} присоединился!`);
            refreshRoom();
            break;
        case 'game_started':
            showToast('Игра началась!');
            startGameScreen();
            break;
        case 'choice_made':
            // No leaderboard updates during game
            break;
        case 'turn_complete':
            refreshGameState();
            break;
        case 'game_finished':
            showResults();
            break;
        case 'state_update':
            refreshGameState();
            break;
        case 'player_disconnected':
            showToast('Игрок отключился');
            refreshRoom();
            break;
    }
}

async function refreshRoom() {
    try {
        const response = await fetch(`${API_URL}/rooms/${state.roomCode}`);
        if (response.ok) {
            const room = await response.json();
            updateLobby(room);
        }
    } catch (error) {
        console.error('Error refreshing room:', error);
    }
}

// Start game
async function startGame() {
    try {
        const response = await fetch(`${API_URL}/rooms/${state.roomCode}/start?player_id=${state.playerId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || 'Ошибка запуска игры', true);
            return;
        }

        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'game_started' }));
        }

        startGameScreen();
    } catch (error) {
        showToast('Ошибка запуска игры', true);
        console.error(error);
    }
}

async function startGameScreen() {
    showScreen('game-screen');
    await refreshGameState();
}

async function refreshGameState() {
    try {
        const response = await fetch(`${API_URL}/rooms/${state.roomCode}/state`);
        if (!response.ok) return;

        const data = await response.json();

        if (data.room.status === 'finished') {
            showResults();
            return;
        }

        updateGameUI(data);
    } catch (error) {
        console.error('Error refreshing game state:', error);
    }
}

function updateGameUI(data) {
    const room = data.room;
    const card = data.current_card;
    const currentPlayer = data.current_player;

    document.getElementById('card-number').textContent = room.current_card_index + 1;
    document.getElementById('total-cards').textContent = room.total_cards;
    document.getElementById('current-player-name').textContent = currentPlayer ? currentPlayer.nickname : '';

    if (card) {
        const cardImageUrl = `/cards/${card.image_path}`;
        const loader = document.getElementById('card-loader');

        // Show loader
        loader.classList.add('loading');

        // Preload image
        const img = new Image();
        img.onload = () => {
            document.getElementById('card-front').style.backgroundImage = `url('${cardImageUrl}')`;
            document.getElementById('card-back').style.backgroundImage = `url('${cardImageUrl}')`;
            loader.classList.remove('loading');
        };
        img.onerror = () => {
            loader.classList.remove('loading');
        };
        img.src = cardImageUrl;

        state.currentCardType = card.card_type;

        // Reset card to back side (unflipped) for new card
        state.cardFlipped = false;
        document.getElementById('card-flipper').classList.remove('flipped');
    }

    const isMyTurn = currentPlayer && currentPlayer.id === state.playerId;
    state.choiceMade = false;

    // Hide all choice button containers first
    document.getElementById('choice-buttons-do-or-drink').classList.add('hidden');
    document.getElementById('choice-buttons-truth-or-drink').classList.add('hidden');

    // Show appropriate buttons based on card type
    if (isMyTurn && card) {
        if (card.card_type === 'truth_or_drink') {
            document.getElementById('choice-buttons-truth-or-drink').classList.remove('hidden');
        } else {
            // Default: do_or_drink
            document.getElementById('choice-buttons-do-or-drink').classList.remove('hidden');
        }
    }

    document.getElementById('ready-button').classList.add('hidden');
    document.getElementById('waiting-turn').classList.toggle('hidden', isMyTurn);
    document.getElementById('waiting-player-name').textContent = currentPlayer ? currentPlayer.nickname : '';
}

async function makeChoice(choice) {
    try {
        const response = await fetch(`${API_URL}/rooms/${state.roomCode}/choice?player_id=${state.playerId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ choice: choice })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || 'Ошибка', true);
            return;
        }

        state.choiceMade = true;

        // Hide all choice buttons
        document.getElementById('choice-buttons-do-or-drink').classList.add('hidden');
        document.getElementById('choice-buttons-truth-or-drink').classList.add('hidden');
        document.getElementById('ready-button').classList.remove('hidden');

        let choiceText;
        if (choice === 'drink') {
            choiceText = state.currentCardType === 'truth_or_drink' ? 'ПЕЙ!' : 'ПЕЙ!';
        } else if (choice === 'skip') {
            choiceText = 'ПРОПУСК';
        } else {
            choiceText = 'СДЕЛАЙ!';
        }
        document.getElementById('choice-made-text').textContent = `Твой выбор: ${choiceText}`;

        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                type: 'choice_made',
                player: state.playerId,
                choice: choice
            }));
        }
    } catch (error) {
        showToast('Ошибка выбора', true);
        console.error(error);
    }
}

async function confirmReady() {
    try {
        const response = await fetch(`${API_URL}/rooms/${state.roomCode}/next?player_id=${state.playerId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || 'Ошибка', true);
            return;
        }

        const data = await response.json();

        if (data.status === 'game_finished') {
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({ type: 'game_finished' }));
            }
            showResults();
        } else {
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({ type: 'turn_complete' }));
            }
            await refreshGameState();
        }
    } catch (error) {
        showToast('Ошибка', true);
        console.error(error);
    }
}

function flipCard() {
    state.cardFlipped = !state.cardFlipped;
    const flipper = document.getElementById('card-flipper');
    flipper.classList.toggle('flipped', state.cardFlipped);
}

async function showResults() {
    showScreen('results-screen');

    try {
        const response = await fetch(`${API_URL}/rooms/${state.roomCode}/leaderboard`);
        if (!response.ok) return;

        const data = await response.json();

        document.getElementById('final-drink-leaderboard').innerHTML = data.drink_leaderboard.map((p, i) => `
            <li class="${p.is_winner ? 'winner' : ''}">
                <div class="player-info">
                    <span class="rank">${i + 1}</span>
                    <span>${p.nickname}</span>
                </div>
                <span class="score">${p.score}</span>
            </li>
        `).join('');

        document.getElementById('final-action-leaderboard').innerHTML = data.action_leaderboard.map((p, i) => `
            <li class="${p.is_winner ? 'winner' : ''}">
                <div class="player-info">
                    <span class="rank">${i + 1}</span>
                    <span>${p.nickname}</span>
                </div>
                <span class="score">${p.score}</span>
            </li>
        `).join('');
    } catch (error) {
        console.error('Error loading results:', error);
    }
}

function backToMenu() {
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }
    state = {
        playerId: null,
        roomCode: null,
        isHost: false,
        selectedGameId: null,
        ws: null,
        choiceMade: false,
        currentCardType: null,
        cardFlipped: false
    };
    showScreen('main-menu');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    showScreen('main-menu');
});
