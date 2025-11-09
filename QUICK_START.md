# 🚀 Quick Start Guide - AI Tabletop Game Platform

## Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (optional, for AI functionality)

## 1️⃣ Backend Setup (5 minutes)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed initial data (adds 5 games)
python scripts/seed_data.py

# Start backend server
uvicorn main:socket_app --reload --port 8000
```

**Backend will be running at**: http://localhost:8000

**API Documentation**: http://localhost:8000/docs

## 2️⃣ Frontend Setup (3 minutes)

```bash
# Open a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend will be running at**: http://localhost:5173

## 3️⃣ Optional: Configure OpenAI API

For AI agent functionality, create a `.env` file in the `backend` directory:

```env
OPENAI_API_KEY=sk-your-api-key-here
```

**Note**: Without an API key, the platform will use a test key. AI decisions will fail gracefully with fallback actions.

## 🎮 Using the Platform

### Create a Game Room
1. Open http://localhost:5173
2. Click on "犯罪现场" (Crime Scene) game
3. Click "立即开始" (Play Now)
4. Configure player settings (4-8 players)
5. Click "创建房间" (Create Room)

### Join a Game
1. Copy the room code (e.g., "ABC123")
2. Share with friends
3. Friends can enter code to join
4. Or use "填充AI" (Fill with AI) to add AI players

### Start Playing
1. Click "开始游戏" (Start Game) when ready
2. Take turns investigating locations
3. Reveal clues and make accusations
4. AI players will make decisions automatically

### Browse Games
- Click "游戏大厅" (Game Library) in navigation
- View available and coming soon games
- Filter by availability
- Click on game cards for details

## 🧪 Run Tests

```bash
cd backend
pytest tests/ -v

# Quick test (no verbose)
pytest tests/ -q

# With coverage
pytest tests/ --cov=src
```

**Expected**: 80 tests passing ✅

## 📁 Key URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | Main application |
| Backend | http://localhost:8000 | API server |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health Check | http://localhost:8000/health | Server status |

## 🎯 Available Game Types

1. **犯罪现场 (Crime Scene)** ✅ Available
   - Players: 4-8
   - Duration: ~60 minutes
   - Status: Fully playable

2. **狼人杀 (Werewolf)** 🔜 Coming Soon
3. **阿瓦隆 (Avalon)** 🔜 Coming Soon
4. **谁是卧底 (Undercover)** 🔜 Coming Soon
5. **德州扑克 (Texas Hold'em)** 🔜 Coming Soon

## 🛠️ Troubleshooting

### Backend won't start
- Check if port 8000 is already in use
- Ensure virtual environment is activated
- Verify all dependencies are installed: `pip list`

### Frontend won't start
- Check if port 5173 is already in use
- Delete `node_modules` and run `npm install` again
- Clear npm cache: `npm cache clean --force`

### Database issues
- Delete `vbrpg.db` and run migrations again:
  ```bash
  rm vbrpg.db
  alembic upgrade head
  python scripts/seed_data.py
  ```

### AI not working
- Check `OPENAI_API_KEY` is set correctly
- Verify API key is valid
- Check backend logs for errors
- Platform works without AI (uses fallback actions)

### WebSocket connection issues
- Ensure backend is running
- Check CORS settings in `backend/.env`
- Verify frontend `VITE_WS_URL` matches backend URL

## 📊 Development Commands

### Backend
```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Format code
black src/
isort src/

# Lint
flake8 src/
```

### Frontend
```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint

# Format
npm run format
```

## 🎨 Project Structure Overview

```
vbrpg/
├── backend/              # FastAPI backend
│   ├── src/             # Source code
│   │   ├── api/         # REST endpoints
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   ├── websocket/   # Socket.IO handlers
│   │   └── integrations/# External services (LLM)
│   ├── tests/           # Test suite
│   ├── alembic/         # Database migrations
│   └── scripts/         # Utility scripts
│
└── frontend/            # Vue 3 frontend
    ├── src/
    │   ├── views/       # Page components
    │   ├── components/  # Reusable components
    │   ├── stores/      # Pinia state management
    │   ├── services/    # API clients
    │   └── router/      # Vue Router
    └── public/          # Static assets
```

## 🔐 Default Configuration

### Backend (.env)
```env
DATABASE_URL=sqlite+aiosqlite:///./vbrpg.db
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
```

## 🚨 Important Notes

1. **Development Mode**: Current setup is for development only
2. **Database**: Using SQLite (switch to PostgreSQL for production)
3. **Authentication**: Mock authentication (implement proper auth for production)
4. **CORS**: Configured for localhost (update for production domains)
5. **API Keys**: Never commit API keys to version control

## 📚 Documentation

- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Task Progress**: See `specs/001-ai-game-platform/tasks.md`
- **API Contracts**: See `specs/001-ai-game-platform/contracts/`
- **Architecture**: See `specs/001-ai-game-platform/plan.md`

## 🎯 Quick Test Scenarios

### Scenario 1: Solo with AI
1. Create room with 4 players minimum
2. Use "填充AI" to add 3 AI players
3. Start game and observe AI making moves

### Scenario 2: Multiplayer
1. Create room on computer A
2. Copy room code
3. Join from computer B using the code
4. Fill remaining slots with AI
5. Start game

### Scenario 3: Browse Games
1. Go to Game Library
2. Filter by "可游玩" (Available)
3. Click on Crime Scene
4. View rules and details
5. Click "立即开始" (Play Now)

## ✅ Success Indicators

You know everything is working when:
- ✅ Backend shows "Application startup complete"
- ✅ Frontend opens at http://localhost:5173
- ✅ Game library displays 5 games
- ✅ Can create and join rooms
- ✅ AI players make moves during their turn
- ✅ All 80 tests pass

## 🆘 Get Help

If you encounter issues:
1. Check backend terminal for error logs
2. Check frontend console (F12) for errors
3. Run tests to identify problems: `pytest tests/ -v`
4. Review `IMPLEMENTATION_SUMMARY.md` for architecture details
5. Check if all dependencies are installed correctly

---

**Ready to play?** Start both servers and visit http://localhost:5173 🎮
