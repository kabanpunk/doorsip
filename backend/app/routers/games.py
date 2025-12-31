from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from ..models import Game, Card
from ..schemas import GameOut

router = APIRouter()


@router.get("/", response_model=List[GameOut])
def get_games(db: Session = Depends(get_db)):
    games = db.query(
        Game.id,
        Game.name,
        Game.description,
        func.count(Card.id).label("cards_count")
    ).outerjoin(Card).group_by(Game.id).all()

    return [
        GameOut(
            id=g.id,
            name=g.name,
            description=g.description,
            cards_count=g.cards_count
        )
        for g in games
    ]


@router.get("/{game_id}", response_model=GameOut)
def get_game(game_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    cards_count = db.query(Card).filter(Card.game_id == game_id).count()
    return GameOut(
        id=game.id,
        name=game.name,
        description=game.description,
        cards_count=cards_count
    )
