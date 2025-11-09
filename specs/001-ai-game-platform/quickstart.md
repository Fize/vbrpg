# Quickstart Guide: AI-Powered Tabletop Game Platform

**Last Updated**: 2025-11-08
**Target Audience**: Developers setting up local development environment

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher  
- **npm**: 9.x or higher
- **Docker** (optional): For containerized development
- **Git**: For version control

**Note**: SQLite is included with Python, no separate database installation needed!

---

## Quick Setup (5 minutes)

### Option A: Docker Compose (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd vbrpg

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Seed initial data
docker-compose exec backend python scripts/seed_data.py

# Access application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**That's it!** Skip to [Testing the Setup](#testing-the-setup)

---

### Option B: Manual Setup

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=sqlite+aiosqlite:///./data/vbrpg.db
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
ENVIRONMENT=development
LOG_LEVEL=DEBUG
EOF

# Create data directory
mkdir -p data

# Run migrations (creates SQLite database)
alembic upgrade head

# Seed initial data (Crime Scene game)
python scripts/seed_data.py

# Start backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend should now be running at**: http://localhost:8000
**Database file created at**: `backend/data/vbrpg.db`

#### 3. Frontend Setup

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
VITE_ENVIRONMENT=development
EOF

# Start development server
npm run dev
```

**Frontend should now be running at**: http://localhost:5173

#### 2. Initialize SQLite Database

The database is automatically created when you run migrations in the backend setup. The SQLite database file will be located at:
- `backend/data/vbrpg.db` (main database)
- `backend/data/vbrpg.db-wal` (Write-Ahead Log for concurrency)
- `backend/data/vbrpg.db-shm` (Shared memory file)

**Backup the database**:
```bash
# Simple file copy (WAL mode is safe for this)
cp backend/data/vbrpg.db backend/data/vbrpg.db.backup

# Or use SQLite backup command
sqlite3 backend/data/vbrpg.db ".backup 'backend/data/vbrpg.db.backup'"
```

---

## Project Structure

```
vbrpg/
├── backend/
│   ├── src/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── services/        # Business logic
│   │   ├── api/             # FastAPI routes
│   │   ├── websocket/       # Socket.IO handlers
│   │   ├── integrations/    # LLM integration
│   │   └── utils/           # Helpers
│   ├── tests/
│   ├── alembic/             # Database migrations
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/      # Vue components
│   │   ├── views/           # Page views
│   │   ├── stores/          # Pinia stores
│   │   ├── services/        # API/WebSocket clients
│   │   └── router/          # Vue Router
│   ├── tests/
│   ├── package.json
│   └── vite.config.js
├── specs/
│   └── 001-ai-game-platform/
│       ├── spec.md          # Feature specification
│       ├── plan.md          # This implementation plan
│       ├── research.md      # Technical decisions
│       ├── data-model.md    # Database schema
│       └── contracts/       # API contracts
├── docker-compose.yml
└── README.md
```

---

## Testing the Setup

### 1. Health Check

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","timestamp":"2025-11-08T12:00:00Z"}

# Check API documentation
open http://localhost:8000/docs  # Opens Swagger UI
```

### 2. Create Guest Account (REST API)

```bash
curl -X POST http://localhost:8000/api/v1/players/guest \
  -H "Content-Type: application/json" \
  -c cookies.txt

# Expected response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "username": "Guest_快乐_熊猫",
#   "is_guest": true,
#   "created_at": "2025-11-08T12:00:00Z"
# }
```

### 3. List Available Games

```bash
curl http://localhost:8000/api/v1/games

# Expected response:
# [
#   {
#     "id": "...",
#     "name": "犯罪现场",
#     "slug": "crime-scene",
#     "is_available": true,
#     "min_players": 4,
#     "max_players": 8
#   }
# ]
```

### 4. Create Game Room

```bash
curl -X POST http://localhost:8000/api/v1/rooms \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "game_type_slug": "crime-scene",
    "max_players": 6,
    "min_players": 4
  }'

# Expected response:
# {
#   "id": "...",
#   "code": "ABCD1234",
#   "status": "Waiting",
#   "game_type": {...},
#   "max_players": 6,
#   "current_player_count": 1
# }
```

### 5. Test WebSocket Connection (JavaScript)

Open browser console at http://localhost:5173 and run:

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000', {
  withCredentials: true
});

socket.on('connect', () => {
  console.log('✅ Connected to WebSocket server');
  
  // Join a room
  socket.emit('join_room', { room_code: 'ABCD1234' }, (response) => {
    console.log('Join room response:', response);
  });
});

socket.on('player_joined', (data) => {
  console.log('🎮 Player joined:', data);
});
```

---

## Running Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_player_service.py

# Run integration tests
pytest tests/integration/

# View coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test:unit

# Run unit tests in watch mode
npm run test:unit -- --watch

# Run E2E tests (requires backend running)
npm run test:e2e

# Run E2E tests in UI mode
npm run test:e2e -- --ui
```

---

## Common Development Tasks

### Create Database Migration

```bash
cd backend
source venv/bin/activate

# Auto-generate migration from model changes
alembic revision --autogenerate -m "add new field to player"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Add New API Endpoint

1. **Define route** in `backend/src/api/routes/`:

```python
# backend/src/api/routes/players.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/players", tags=["Players"])

@router.get("/me/history")
async def get_player_history(
    player: Player = Depends(get_current_player)
):
    """Get player's game history"""
    sessions = await game_service.get_player_history(player.id)
    return {"sessions": sessions}
```

2. **Update OpenAPI spec** in `specs/001-ai-game-platform/contracts/rest-api.yaml`

3. **Add tests** in `backend/tests/integration/test_player_api.py`

### Add New WebSocket Event

1. **Define handler** in `backend/src/websocket/handlers.py`:

```python
@sio.event
async def request_hint(sid, data):
    """Handle hint request during gameplay"""
    room_code = data['room_code']
    hint = await game_service.generate_hint(room_code)
    
    await sio.emit('hint_provided', {
        'room_code': room_code,
        'hint': hint
    }, room=room_code)
```

2. **Update contract** in `specs/001-ai-game-platform/contracts/websocket-events.md`

3. **Add frontend handler** in `frontend/src/services/websocket.ts`

### Add New Vue Component

```bash
cd frontend/src/components

# Create component file
touch GameTimer.vue
```

```vue
<!-- frontend/src/components/GameTimer.vue -->
<template>
  <div class="game-timer">
    <el-progress 
      :percentage="percentage" 
      :color="color"
      :format="formatTime"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  remainingSeconds: number;
  totalSeconds: number;
}>();

const percentage = computed(() => 
  (props.remainingSeconds / props.totalSeconds) * 100
);

const color = computed(() => 
  percentage.value > 50 ? '#67C23A' : '#F56C6C'
);

const formatTime = () => {
  const mins = Math.floor(props.remainingSeconds / 60);
  const secs = props.remainingSeconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};
</script>
```

---

## Debugging

### Backend Debugging (VS Code)

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "ENVIRONMENT": "development"
      }
    }
  ]
}
```

### Frontend Debugging

```javascript
// frontend/src/services/websocket.ts

// Enable Socket.IO debug logs
localStorage.debug = 'socket.io-client:*';

// Use Vue DevTools for state inspection
// Install: https://devtools.vuejs.org/
```

### Database Debugging

```bash
# Connect to SQLite database
sqlite3 backend/data/vbrpg.db

# Useful SQLite commands
.tables  -- List tables
.schema players  -- Show table schema
SELECT * FROM game_rooms WHERE status = 'Waiting';

# Enable column headers and better formatting
.headers on
.mode column

# Check database integrity
PRAGMA integrity_check;

# View active connections (WAL mode info)
PRAGMA wal_checkpoint;
```

---

## Environment Variables Reference

### Backend (.env)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| DATABASE_URL | Yes | SQLite database path | `sqlite+aiosqlite:///./data/vbrpg.db` |
| OPENAI_API_KEY | Yes | OpenAI API key for LLM | `sk-...` |
| SECRET_KEY | Yes | Session encryption key | Random 32-byte string |
| ENVIRONMENT | Yes | Deployment environment | `development`, `production` |
| LOG_LEVEL | No | Logging verbosity | `DEBUG`, `INFO`, `WARNING` |
| CORS_ORIGINS | No | Allowed origins | `http://localhost:5173,http://localhost:3000` |

### Frontend (.env)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| VITE_API_URL | Yes | Backend API base URL | `http://localhost:8000` |
| VITE_WS_URL | Yes | WebSocket server URL | `http://localhost:8000` |
| VITE_ENVIRONMENT | Yes | Environment mode | `development`, `production` |

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.11+

# Check database connection
psql -h localhost -U vbrpg_user -d vbrpg

# Check for port conflicts
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# View logs
tail -f logs/app.log
```

### Frontend won't build

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18.x+

# Clear Vite cache
rm -rf node_modules/.vite
```

### WebSocket connection fails

```bash
# Check CORS settings in backend/main.py
# Ensure frontend origin is allowed

# Test WebSocket with curl
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
  http://localhost:8000/socket.io/

# Check browser console for errors
```

### Database migration issues

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Reset to specific version
alembic downgrade <revision>

# Recreate database (nuclear option)
dropdb vbrpg && createdb vbrpg
alembic upgrade head
python scripts/seed_data.py
```

---

## Next Steps

1. **Read the specification**: `specs/001-ai-game-platform/spec.md`
2. **Review data model**: `specs/001-ai-game-platform/data-model.md`
3. **Explore API contracts**: `specs/001-ai-game-platform/contracts/`
4. **Join the development**:
   - Pick a task from `specs/001-ai-game-platform/tasks.md` (coming soon)
   - Create a feature branch: `git checkout -b feature/your-feature`
   - Write tests first (TDD approach)
   - Submit PR for review

---

## Useful Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Socket.IO Python**: https://python-socketio.readthedocs.io/
- **Vue 3 Guide**: https://vuejs.org/guide/
- **Element-Plus**: https://element-plus.org/
- **LangChain**: https://python.langchain.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Alembic**: https://alembic.sqlalchemy.org/

---

## Support

- **Issues**: Create an issue in the repository
- **Questions**: Use GitHub Discussions
- **Documentation**: Check `specs/` directory for detailed docs

**Happy Coding! 🎮**
