# Prediction Market Starter Kit

This repository provides a minimal proof‑of‑concept prediction market with an
automated market maker built using FastAPI, SQLAlchemy and a simple HTML/JS
frontend. It follows the system design outlined in the accompanying notes and
is intended as a starting point for experimentation and further development.

## Features

- **User registration & login** with hashed passwords and a starting balance.
- **Market creation** via an admin endpoint (see `frontend/admin.html`).
- **LMSR automated market maker** powering binary markets with continuous
  liquidity and dynamically adjusting prices.
- **Bet placement** with balance checks and cost calculation based on the
  LMSR cost function.
- **Market resolution** which pays out winning shares and freezes prices.
- A basic **frontend** that lists markets, shows details and allows users to
  log in, register, place bets and create markets.
- **CORS** enabled for ease of deployment when the backend and frontend are
  served from different hosts.

## Folder Structure

```
prediction-market/
│
├── backend/
│   ├── main.py          # FastAPI application and API endpoints
│   ├── models.py        # SQLAlchemy ORM models (User, Market, Bet)
│   ├── database.py      # Database engine and session management
│   ├── market_logic.py  # LMSR cost and price calculations
│   └── requirements.txt # Python dependencies
│
├── frontend/
│   ├── index.html       # List of markets
│   ├── market.html      # Market detail and betting interface
│   ├── admin.html       # Admin page to create markets
│   ├── login.html       # Login and registration page
│   ├── script.js        # Shared JS functions
│   └── styles.css       # Basic styling
│
└── README.md
```

## Getting Started

### 1. Backend Setup

1. **Create a virtual environment** (optional but recommended):

   ```bash
   cd prediction-market/backend
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the database**:

   - By default the app uses a local SQLite database at `./market.db`. This is
     fine for local development.
   - To use PostgreSQL or another database, set the `DATABASE_URL` environment
     variable before starting the server. For example:

     ```bash
     export DATABASE_URL="postgresql+psycopg2://user:password@hostname:5432/dbname"
     ```

4. **Run the server**:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`. Visit
   `http://localhost:8000/docs` to explore the automatically generated OpenAPI
   documentation and try the endpoints interactively.

### 2. Frontend Usage

The frontend consists of static HTML, CSS and JavaScript files that can be
served by any static hosting service (GitHub Pages, Vercel, Netlify, etc.).
For local testing you can simply open the files in your browser.

To load data from your running backend, update the `apiBase` constant at the
top of `frontend/script.js` if your backend is served on a different origin.
For example:

```js
// In frontend/script.js
const apiBase = 'https://your-backend.onrender.com';
```

Then deploy or open `frontend/index.html` in a browser. You should be able
to register a user, log in, browse markets, create new markets (via
`admin.html`) and place bets.

## Notes & Next Steps

This starter kit is deliberately minimal. It lacks many features required for
a production system, including but not limited to authentication tokens,
permissions, input sanitisation, rate limiting and robust error handling.
Possible extensions include:

- Implement JWT‑based authentication so that user sessions are secure.
- Add endpoints to list a user's past bets and market history.
- Integrate a charting library on the frontend to visualise price changes.
- Support multi‑outcome markets by generalising the LMSR to more than two
  outcomes.
- Switch to an async database driver (e.g. `asyncpg`) and the async
  capabilities of FastAPI/SQLAlchemy.
- Deploy the backend on a platform like Render, Railway or Supabase and the
  frontend on GitHub Pages or Vercel for a fully serverless experience.

Enjoy building your prediction market!