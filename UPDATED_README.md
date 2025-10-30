# Prediction Market (Educational & Experimental Project)

This repository provides a minimal **proof-of-concept prediction market** with an automated market maker built using **FastAPI**, **SQLAlchemy**, and a **simple HTML/JS frontend**.  
It follows the original system design outlined in the accompanying notes and serves as a **learning and experimentation toolkit**, **not for profit or real trading**.

---

## ⚠️ Disclaimer & Acknowledgment

> This project is for **educational and experimental purposes only**.  
> All markets, balances, and outcomes are **virtual** and have **no monetary value**.  
> It is **not a platform for investment, gambling, or profit-making**.  
>
> Development involved the use of **AI tools including ChatGPT** for **brainstorming, debugging, and documentation support**.  
> All outputs were reviewed and refined by the author to ensure technical accuracy and educational value.

---

## ✨ Features

- **User registration & login** with hashed passwords and a virtual starting balance.  
- **Market creation** via an admin endpoint (see `frontend/admin.html`).  
- **LMSR automated market maker** powering binary markets with continuous liquidity and dynamic pricing.  
- **Bet placement** with balance checks and LMSR-based cost functions.  
- **Market resolution** with payout logic for winning shares and price freeze after close.  
- **User portal** displaying balances, transactions, and claimable daily bonuses.  
- **CORS-enabled API** for flexible backend/frontend hosting.  
- **Frontend visualization** for price history and market expiration times.

---

## 🗂️ Folder Structure

```
prediction-market/
│
├── backend/
│   ├── main.py          # FastAPI app and API endpoints
│   ├── models.py        # SQLAlchemy ORM models (User, Market, Bet)
│   ├── market_logic.py  # LMSR pricing & liquidity logic
│   ├── database.py      # Database setup and session management
│   ├── utils.py         # Helper functions (timestamps, admin checks, etc.)
│   └── requirements.txt # Python dependencies
│
├── frontend/
│   ├── index.html       # List of active/inactive markets
│   ├── market.html      # Market detail and betting interface
│   ├── admin.html       # Admin-only page for market creation/resolution
│   ├── portal.html      # User portal: balances, transactions, bonus claim
│   ├── login.html       # Login/registration page
│   ├── script.js        # Shared JS functions and API logic
│   └── styles.css       # Base styling for layout and cards
│
└── README.md
```

---

## ⚙️ Getting Started

### 1. Backend Setup

Create and activate a virtual environment:

```bash
cd prediction-market/backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure your database:

- Default: local SQLite at `./market.db`
- Optional (PostgreSQL):

  ```bash
  export DATABASE_URL="postgresql+psycopg2://user:password@hostname:5432/dbname"
  ```

Run the server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Access API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Frontend Setup

The frontend is static and can be opened directly or hosted anywhere (e.g., GitHub Pages, Vercel, Netlify).

To connect to your backend, update the following line in `frontend/script.js`:

```js
const apiBase = 'https://your-backend.onrender.com';
```

Then open `frontend/index.html` in your browser to register, log in, browse, and place trades.

---

## 🧩 Example Functionality

- Create or view binary markets with expiration timestamps.  
- Place YES/NO bets with LMSR-based cost updates.  
- View your transaction and balance history.  
- Claim a **daily reward** (50 credits every 23 hours if balance ≤ 500).  
- Admins can resolve or delete expired markets.  

---

## 💡 Next Steps (Suggested Enhancements)

- Add JWT-based authentication for session security.  
- Include leaderboard and user performance analytics.  
- Enable multi-outcome markets.  
- Integrate real-time chart updates (WebSocket or polling).  
- Deploy via Render (backend) + Vercel or GitHub Pages (frontend).

---

## 🧠 Learning Focus

This project demonstrates:
- The LMSR (Logarithmic Market Scoring Rule) market-maker formula  
- Integration of **FastAPI + SQLAlchemy + JS frontend**  
- Time-based expiration and balance logic  
- Clean REST API design for learning web development concepts  
- Ethical, AI-assisted experimentation in open-source environments  

---

## 📜 License

**Creative Commons Attribution–NonCommercial–ShareAlike 4.0 (CC BY-NC-SA 4.0)**  
You may remix, adapt, and build upon this work **non-commercially**, provided you credit the author and share alike.
