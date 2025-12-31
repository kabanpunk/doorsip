# DoOrSip

Party game where players choose to either DO the challenge or SIP a drink!

## Quick Start

### Prerequisites
- Docker
- Docker Compose

### Launch

```bash
# Clone/download the project and navigate to the directory
cd doorsip

# Start all services
docker-compose up -d

# View logs (optional)
docker-compose logs -f
```

The app will be available at: **http://localhost**

### Stop

```bash
docker-compose down
```

### Full reset (including database)

```bash
docker-compose down -v
```

---

## Adding Games and Cards

### Step 1: Add Card Images

1. Create a folder for your game inside `data/cards/`:
   ```bash
   mkdir -p data/cards/mygame
   ```

2. Copy your card images (PNG, JPG) into the folder:
   ```bash
   cp /path/to/cards/*.png data/cards/mygame/
   ```

   Example structure:
   ```
   data/cards/
   └── mygame/
       ├── card_001.png
       ├── card_002.png
       └── card_003.png
   ```

### Step 2: Add Game to Database

Connect to the database and run SQL:

```bash
# Connect to PostgreSQL in container
docker exec -it doorsip_db psql -U doorsip -d doorsip
```

Then run SQL commands:

```sql
-- Create a new game
INSERT INTO games (name, description) VALUES
('My Awesome Game', 'Description of the game');

-- Check the game ID (should be 1 if first game)
SELECT * FROM games;

-- Add cards for the game (use the game ID from above)
INSERT INTO cards (game_id, image_path, drink_points, action_points) VALUES
(1, 'mygame/card_001.png', 1, 2),
(1, 'mygame/card_002.png', 2, 1),
(1, 'mygame/card_003.png', 3, 3);

-- Exit psql
\q
```

### SQL Quick Reference

```sql
-- View all games
SELECT * FROM games;

-- View cards for a specific game
SELECT * FROM cards WHERE game_id = 1;

-- Update card points
UPDATE cards SET drink_points = 2, action_points = 3 WHERE id = 1;

-- Delete a card
DELETE FROM cards WHERE id = 1;

-- Delete a game (also deletes its cards via CASCADE)
DELETE FROM games WHERE id = 1;
```

### Batch Insert Example

For many cards, use a script:

```sql
-- Insert 10 cards at once
INSERT INTO cards (game_id, image_path, drink_points, action_points) VALUES
(1, 'party/001.png', 1, 2),
(1, 'party/002.png', 2, 1),
(1, 'party/003.png', 1, 3),
(1, 'party/004.png', 3, 1),
(1, 'party/005.png', 2, 2),
(1, 'party/006.png', 1, 1),
(1, 'party/007.png', 2, 3),
(1, 'party/008.png', 3, 2),
(1, 'party/009.png', 1, 2),
(1, 'party/010.png', 2, 2);
```

---

## How to Play

1. **Host** opens the app and clicks "Create Room"
2. Host enters nickname and selects a game
3. Host shares the 6-character room code with friends
4. **Players** click "Join Room" and enter the code + nickname
5. Host clicks "Start Game" when everyone is ready
6. Each turn:
   - Current player sees a card with a challenge
   - Player chooses "DO IT!" (complete the task) or "SIP IT!" (drink)
   - After completing the action, player clicks "DONE!"
   - Turn passes to the next player
7. Game ends when all cards are used
8. Final leaderboards show the Drink Champion and Action Champion!

---

## Project Structure

```
doorsip/
├── docker-compose.yml      # Docker orchestration
├── nginx.conf              # Nginx reverse proxy config
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # FastAPI app entry
│       ├── models.py       # SQLAlchemy models
│       ├── schemas.py      # Pydantic schemas
│       ├── database.py     # DB connection
│       └── routers/
│           ├── games.py    # Games API
│           ├── rooms.py    # Rooms API
│           └── websocket.py # Real-time updates
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── data/
│   ├── init.sql            # Initial DB script
│   └── cards/              # Card images folder
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/games/` | List all games |
| POST | `/api/rooms/create` | Create a new room |
| POST | `/api/rooms/join` | Join existing room |
| GET | `/api/rooms/{code}` | Get room info |
| GET | `/api/rooms/{code}/state` | Get game state |
| POST | `/api/rooms/{code}/start` | Start the game |
| POST | `/api/rooms/{code}/choice` | Make a choice |
| POST | `/api/rooms/{code}/next` | Next turn |
| GET | `/api/rooms/{code}/leaderboard` | Get scores |
| WS | `/ws/{code}` | Real-time updates |

---

## Configuration

Environment variables (set in `docker-compose.yml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql://doorsip:doorsip_secret@db:5432/doorsip | PostgreSQL connection |
| `CARDS_PATH` | /app/cards | Path to card images |

---

## Troubleshooting

**Cards not showing?**
- Check that images exist in `data/cards/`
- Verify the `image_path` in database matches actual file paths
- Restart containers: `docker-compose restart`

**Can't connect to database?**
- Wait for DB to fully start: `docker-compose logs db`
- Reset database: `docker-compose down -v && docker-compose up -d`

**WebSocket not connecting?**
- Check browser console for errors
- Ensure nginx is properly proxying `/ws/` path

---

## License

MIT
