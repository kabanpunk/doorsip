from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base
import enum


class GameStatus(enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class CardType(enum.Enum):
    DO_OR_DRINK = "do_or_drink"       # Сделай или выпей (кнопки: Сделал / Выпил)
    TRUTH_OR_DRINK = "truth_or_drink"  # Правда или выпивка (кнопки: Выпил / Пропустил)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))

    cards = relationship("Card", back_populates="game")


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    image_path = Column(String(255), nullable=False)
    card_type = Column(SQLEnum(CardType), default=CardType.DO_OR_DRINK)
    drink_points = Column(Integer, default=1)
    action_points = Column(Integer, default=1)

    game = relationship("Game", back_populates="cards")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), unique=True, index=True, nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    status = Column(SQLEnum(GameStatus), default=GameStatus.WAITING)
    current_player_index = Column(Integer, default=0)
    current_card_index = Column(Integer, default=0)

    game = relationship("Game")
    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")
    used_cards = relationship("RoomCard", back_populates="room", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    nickname = Column(String(50), nullable=False)
    is_host = Column(Boolean, default=False)
    drink_score = Column(Integer, default=0)
    action_score = Column(Integer, default=0)

    room = relationship("Room", back_populates="players")


class RoomCard(Base):
    __tablename__ = "room_cards"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)

    room = relationship("Room", back_populates="used_cards")
    card = relationship("Card")
