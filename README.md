# AI-Powered Tabletop Game Platform

A multiplayer web-based platform for playing Crime Scene tabletop games with friends, powered by AI agents to fill empty player slots.

## Features

- **Guest Mode**: Play immediately without account registration
- **AI-Powered**: Intelligent AI agents fill empty player slots using LLMs
- **Real-Time Multiplayer**: WebSocket-based game state synchronization
- **Responsive Web UI**: Works on desktop and mobile browsers
- **Simple Room System**: Create or join games with 6-character room codes
- **Player Accounts**: Optional registration to track stats and history

## Tech Stack

### Backend
- **Python 3.11+**: Core backend language
- **FastAPI**: Modern async web framework
- **python-socketio**: WebSocket communication (Socket.IO protocol)
- **LangChain**: LLM integration framework
- **SQLAlchemy**: Async ORM for database access
- **SQLite**: Embedded database (WAL mode for concurrency)

### Frontend
- **Vue 3**: Progressive JavaScript framework (Composition API)
- **Element-Plus**: Vue 3 UI component library
- **Vite**: Fast build tool and dev server
- **Pinia**: State management
- **Vue Router**: Client-side routing
- **socket.io-client**: WebSocket client library

## Quick Start

### Prerequisites

- **Python 3.11+**: [Download Python](https://www.python.org/downloads/)
- **Node.js 18+**: [Download Node.js](https://nodejs.org/)
- **Git**: [Download Git](https://git-scm.com/)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/vbrpg.git
   cd vbrpg
   ```

2. **Set up the backend**:
   ```bash
   cd backend
   
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create .env file
   cp .env.example .env
   # Edit .env and add your LLM API keys (OpenAI, Anthropic, etc.)
   
   # Initialize database
   python -m alembic upgrade head
   ```

3. **Set up the frontend**:
   ```bash
   cd ../frontend
   
   # Install dependencies
   npm install
   
   # Create .env file
   cp .env.example .env.local
   # Edit .env.local if needed (API URL defaults to http://localhost:8000)
   ```

### Running the Application

1. **Start the backend** (from `backend/` directory):
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend** (from `frontend/` directory, in a new terminal):
   ```bash
   npm run dev
   ```

3. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Usage

### Creating a Game

1. Open the application in your browser
2. Click "Create Room"
3. Configure game settings:
   - Number of players (2-6)
   - Difficulty level (Easy/Medium/Hard)
   - Turn time limit (30-300 seconds)
   - Enable/disable AI narrator
4. Click "Create" - you'll receive a 6-character room code
5. Share the room code with friends

### Joining a Game

1. Click "Join Room"
2. Enter the 6-character room code
3. Wait in the lobby until the room creator starts the game
4. When the game starts, AI agents will fill any empty slots

### Playing the Game

- **Your Turn**: Take actions when it's your turn (investigate, question, move, examine, etc.)
- **Turn Timer**: Watch the countdown - you have limited time per turn
- **Chat**: Communicate with other players using the in-game chat
- **Reconnection**: If disconnected, rejoin within 5 minutes to resume your game

### Player Accounts (Optional)

- Create an account to track your game statistics
- View game history and win rates
- Upgrade from guest to registered account
- Guest accounts are retained for 30 days

## Development

### Project Structure

```
vbrpg/
├── backend/
│   ├── src/
│   │   ├── api/           # REST API endpoints
│   │   ├── database.py    # Database setup and session management
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # Business logic services
│   │   ├── websocket/     # WebSocket event handlers
│   │   ├── utils/         # Utility functions
│   │   └── main.py        # FastAPI application entry point
│   ├── tests/             # Backend tests
│   │   ├── unit/          # Unit tests
│   │   └── integration/   # Integration tests
│   ├── alembic/           # Database migrations
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Backend container
├── frontend/
│   ├── src/
│   │   ├── components/    # Vue components
│   │   ├── views/         # Page views
│   │   ├── stores/        # Pinia state stores
│   │   ├── services/      # API and WebSocket services
│   │   ├── utils/         # Utility functions
│   │   └── main.js        # Vue application entry point
│   ├── tests/             # Frontend tests
│   ├── package.json       # Node dependencies
│   └── Dockerfile         # Frontend container
├── specs/                 # Feature specifications
└── README.md             # This file
```

### Running Tests

**Backend tests**:
```bash
cd backend
source .venv/bin/activate
pytest                    # Run all tests
pytest tests/unit/        # Run unit tests only
pytest tests/integration/ # Run integration tests only
pytest --cov=src          # Run with coverage
```

**Frontend tests**:
```bash
cd frontend
npm run test              # Run unit tests
npm run test:e2e          # Run E2E tests (requires app running)
```

### Database Migrations

**Create a new migration**:
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations**:
```bash
alembic upgrade head
```

**Rollback**:
```bash
alembic downgrade -1
```

### Code Quality

**Backend linting**:
```bash
cd backend
ruff check .              # Check for issues
ruff check . --fix        # Auto-fix issues
```

**Frontend linting**:
```bash
cd frontend
npm run lint              # Check for issues
npm run lint:fix          # Auto-fix issues
```

## Deployment

See [docs/deployment.md](docs/deployment.md) for detailed deployment instructions including:
- Docker Compose setup
- Environment variable configuration
- Production considerations
- Scaling strategies
- Backup procedures

## API Documentation

- **Interactive API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **Detailed API Documentation**: [docs/api.md](docs/api.md)

## Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
LLM_PROVIDER=openai  # or "anthropic"
LLM_MODEL=gpt-4      # or "claude-3-opus-20240229"

# Database
DATABASE_URL=sqlite+aiosqlite:///./game_platform.db

# Security
SECRET_KEY=your_secret_key_here_change_in_production
SESSION_COOKIE_SECURE=false  # Set to true in production with HTTPS

# Server
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO

# Game Settings
TURN_TIMEOUT_SECONDS=60
RECONNECTION_GRACE_PERIOD_MINUTES=5
GUEST_RETENTION_DAYS=30
```

### Frontend Environment Variables

Create `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Performance

The platform is designed to support:
- **50 concurrent game sessions**
- **200 simultaneous players**
- **AI responses within 10 seconds** (95th percentile)
- **Game state sync within 1 second**
- **99% uptime availability**

## Security Considerations

- Input validation on all user inputs
- SQL injection prevention via SQLAlchemy ORM
- XSS protection via content sanitization
- Rate limiting on API endpoints
- Secure session cookies
- CORS configuration

**Note**: This is a proof-of-concept platform with basic security. For production use, consider:
- Implement authentication (JWT, OAuth)
- Add HTTPS/TLS encryption
- Enhanced rate limiting
- DDoS protection
- Security audit and penetration testing

## Limitations

- **Single-session games**: No save/resume functionality
- **LLM dependency**: Game terminates if LLM service fails
- **Reconnection window**: 5 minutes before AI replacement
- **Guest data retention**: 30 days
- **One game type**: Crime Scene (framework ready for more)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[MIT License](LICENSE)

## Support

For issues, questions, or contributions:
- **Issues**: [GitHub Issues](https://github.com/yourusername/vbrpg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/vbrpg/discussions)

## Acknowledgments

- Crime Scene game mechanics inspired by classic tabletop mystery games
- AI integration powered by OpenAI and Anthropic language models
- Built with modern web technologies and best practices
