import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Room, Player, Game, Card, RoomCard, GameStatus
from ..schemas import (
    CreateRoomRequest, JoinRoomRequest, RoomOut, PlayerOut,
    RoomStateOut, CardOut, MakeChoiceRequest, PlayerChoice
)

router = APIRouter()


def generate_room_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def get_sorted_players(room_id: int, db: Session) -> List[Player]:
    """Get all players sorted by id for consistent ordering (including host)."""
    return db.query(Player).filter(Player.room_id == room_id).order_by(Player.id).all()


def get_playing_players(room_id: int, db: Session) -> List[Player]:
    """Get only non-host players sorted by play_order for game turns."""
    return db.query(Player).filter(
        Player.room_id == room_id,
        Player.is_host == False
    ).order_by(Player.play_order).all()


def get_room_out(room: Room, db: Session) -> RoomOut:
    total_cards = db.query(RoomCard).filter(RoomCard.room_id == room.id).count()
    players = get_sorted_players(room.id, db)
    return RoomOut(
        id=room.id,
        code=room.code,
        game_id=room.game_id,
        game_name=room.game.name,
        status=room.status.value,
        players=[
            PlayerOut(
                id=p.id,
                nickname=p.nickname,
                is_host=p.is_host,
                drink_score=p.drink_score,
                action_score=p.action_score
            ) for p in players
        ],
        current_player_index=room.current_player_index,
        current_card_index=room.current_card_index,
        total_cards=total_cards
    )


@router.post("/create", response_model=dict)
def create_room(request: CreateRoomRequest, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == request.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    cards = db.query(Card).filter(Card.game_id == request.game_id).all()
    if not cards:
        raise HTTPException(status_code=400, detail="Game has no cards")

    code = generate_room_code()
    while db.query(Room).filter(Room.code == code).first():
        code = generate_room_code()

    room = Room(code=code, game_id=request.game_id, status=GameStatus.WAITING)
    db.add(room)
    db.flush()

    host = Player(
        room_id=room.id,
        nickname=request.host_nickname,
        is_host=True
    )
    db.add(host)

    shuffled_cards = cards.copy()
    random.shuffle(shuffled_cards)
    for idx, card in enumerate(shuffled_cards):
        room_card = RoomCard(room_id=room.id, card_id=card.id, order_index=idx)
        db.add(room_card)

    db.commit()
    db.refresh(room)
    db.refresh(host)

    return {
        "room_code": room.code,
        "player_id": host.id,
        "room": get_room_out(room, db)
    }


@router.post("/join", response_model=dict)
def join_room(request: JoinRoomRequest, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == request.room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Game already started")

    existing = db.query(Player).filter(
        Player.room_id == room.id,
        Player.nickname == request.nickname
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nickname already taken")

    player = Player(
        room_id=room.id,
        nickname=request.nickname,
        is_host=False
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    db.refresh(room)

    return {
        "player_id": player.id,
        "room": get_room_out(room, db)
    }


@router.get("/{room_code}", response_model=RoomOut)
def get_room(room_code: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return get_room_out(room, db)


@router.get("/{room_code}/state", response_model=RoomStateOut)
def get_room_state(room_code: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    room_out = get_room_out(room, db)
    current_card = None
    current_player = None

    if room.status == GameStatus.PLAYING:
        room_card = db.query(RoomCard).filter(
            RoomCard.room_id == room.id,
            RoomCard.order_index == room.current_card_index
        ).first()
        if room_card:
            card = room_card.card
            current_card = CardOut(
                id=card.id,
                image_path=card.image_path,
                card_type=card.card_type.value,
                drink_points=card.drink_points,
                action_points=card.action_points
            )

        players = get_playing_players(room.id, db)
        if players and room.current_player_index < len(players):
            p = players[room.current_player_index]
            current_player = PlayerOut(
                id=p.id,
                nickname=p.nickname,
                is_host=p.is_host,
                drink_score=p.drink_score,
                action_score=p.action_score
            )

    return RoomStateOut(
        room=room_out,
        current_card=current_card,
        current_player=current_player
    )


@router.post("/{room_code}/start")
def start_game(room_code: str, player_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or not player.is_host:
        raise HTTPException(status_code=403, detail="Only host can start the game")

    if room.status != GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Game already started")

    # Get non-host players
    non_host_players = db.query(Player).filter(
        Player.room_id == room.id,
        Player.is_host == False
    ).all()

    if len(non_host_players) < 1:
        raise HTTPException(status_code=400, detail="Need at least 1 player (besides host)")

    # Assign random play order to non-host players
    random.shuffle(non_host_players)
    for idx, p in enumerate(non_host_players):
        p.play_order = idx

    room.status = GameStatus.PLAYING
    room.current_player_index = 0
    room.current_card_index = 0
    db.commit()

    return {"status": "started"}


@router.post("/{room_code}/choice")
def make_choice(
    room_code: str,
    player_id: int,
    request: MakeChoiceRequest,
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.code == room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != GameStatus.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or player.room_id != room.id:
        raise HTTPException(status_code=403, detail="Invalid player")

    players = get_playing_players(room.id, db)
    current_player = players[room.current_player_index]
    if current_player.id != player_id:
        raise HTTPException(status_code=403, detail="Not your turn")

    room_card = db.query(RoomCard).filter(
        RoomCard.room_id == room.id,
        RoomCard.order_index == room.current_card_index
    ).first()

    if not room_card:
        raise HTTPException(status_code=400, detail="No card available")

    card = room_card.card
    if request.choice == PlayerChoice.DRINK:
        player.drink_score += card.drink_points
    elif request.choice == PlayerChoice.ACTION:
        player.action_score += card.action_points
    # SKIP: no points awarded

    room_card.is_used = True
    db.commit()

    return {"status": "choice_made", "choice": request.choice.value}


@router.post("/{room_code}/next")
def next_turn(room_code: str, player_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != GameStatus.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or player.room_id != room.id:
        raise HTTPException(status_code=403, detail="Invalid player")

    players = get_playing_players(room.id, db)
    current_player = players[room.current_player_index]
    if current_player.id != player_id:
        raise HTTPException(status_code=403, detail="Not your turn")

    total_cards = db.query(RoomCard).filter(RoomCard.room_id == room.id).count()

    room.current_card_index += 1
    if room.current_card_index >= total_cards:
        room.status = GameStatus.FINISHED
        db.commit()
        return {"status": "game_finished"}

    room.current_player_index = (room.current_player_index + 1) % len(players)
    db.commit()

    return {"status": "next_turn"}


@router.get("/{room_code}/leaderboard")
def get_leaderboard(room_code: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.code == room_code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Exclude host from leaderboard
    players = [p for p in room.players if not p.is_host]

    drink_leaderboard = sorted(players, key=lambda p: p.drink_score, reverse=True)
    action_leaderboard = sorted(players, key=lambda p: p.action_score, reverse=True)

    return {
        "drink_leaderboard": [
            {
                "id": p.id,
                "nickname": p.nickname,
                "score": p.drink_score,
                "is_winner": i == 0 and p.drink_score > 0
            }
            for i, p in enumerate(drink_leaderboard)
        ],
        "action_leaderboard": [
            {
                "id": p.id,
                "nickname": p.nickname,
                "score": p.action_score,
                "is_winner": i == 0 and p.action_score > 0
            }
            for i, p in enumerate(action_leaderboard)
        ]
    }
