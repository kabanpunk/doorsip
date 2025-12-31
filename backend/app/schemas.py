from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class CardType(str, Enum):
    DO_OR_DRINK = "do_or_drink"
    TRUTH_OR_DRINK = "truth_or_drink"


class GameBase(BaseModel):
    name: str
    description: Optional[str] = None


class GameOut(GameBase):
    id: int
    cards_count: int = 0

    class Config:
        from_attributes = True


class CardOut(BaseModel):
    id: int
    image_path: str
    card_type: CardType
    drink_points: int
    action_points: int

    class Config:
        from_attributes = True


class PlayerBase(BaseModel):
    nickname: str


class PlayerOut(PlayerBase):
    id: int
    is_host: bool
    drink_score: int
    action_score: int

    class Config:
        from_attributes = True


class CreateRoomRequest(BaseModel):
    game_id: int
    host_nickname: str


class JoinRoomRequest(BaseModel):
    room_code: str
    nickname: str


class RoomOut(BaseModel):
    id: int
    code: str
    game_id: int
    game_name: str
    status: GameStatus
    players: List[PlayerOut]
    current_player_index: int
    current_card_index: int
    total_cards: int

    class Config:
        from_attributes = True


class RoomStateOut(BaseModel):
    room: RoomOut
    current_card: Optional[CardOut] = None
    current_player: Optional[PlayerOut] = None


class PlayerChoice(str, Enum):
    DRINK = "drink"
    ACTION = "action"
    SKIP = "skip"


class MakeChoiceRequest(BaseModel):
    choice: PlayerChoice
