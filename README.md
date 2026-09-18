# 🏦 QuickSave Banking System

> A full-stack demo banking platform — **Python + FastAPI backend** with an **AI financial assistant**,
> atomic transfers, and a polished single-page web app. Runs in one command, no API keys required.

[![CI](https://github.com/zaingulzarzain/QuickSave-Banking-System/actions/workflows/ci.yml/badge.svg)](https://github.com/zaingulzarzain/QuickSave-Banking-System/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)
![Tests](https://img.shields.io/badge/tests-14%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Why this project stands out

| What clients look for | How QuickSave delivers |
|---|---|
| **Clean backend architecture** | Layered FastAPI app: routers → services → SQLAlchemy models, Pydantic v2 schemas, dependency-injected auth |
| **Real-world correctness** | Atomic transfers (debit + credit + ledger rows in one commit), overdraft protection, frozen-account guards |
| **AI/LLM integration** | OpenAI-compatible assistant (works with OpenAI, Azure, Ollama, vLLM…) **with graceful offline fallback** — the demo never breaks without a key |
| **Production habits** | JWT auth, bcrypt hashing, paginated/filtered queries, health checks, seed data, 14 automated tests, CI, Docker |
| **Ready to try** | One command → seeded demo with realistic data, interactive `/docs`, and a full web UI |

---

## 🚀 Quickstart

### Option A — pip (fastest)

```bash
git clone https://github.com/zaingulzarzain/QuickSave-Banking-System.git
cd QuickSave-Banking-System
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open **http://localhost:8000** → the app seeds itself with demo data on first launch.

### Option B — Docker

```bash
docker compose up --build
```

### Option C — Deploy a public live demo (free, ~5 min)

Perfect for your Upwork portfolio — clients click a link, no install needed.

**Render** (easiest — one click):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/zaingulzarzain/QuickSave-Banking-System)

1. Click the button → sign in with GitHub → pick this repo → **Deploy**
2. Wait ~3–5 min for the first build → you get `https://quicksave-xxxx.onrender.com`
3. (Optional) add `OPENAI_API_KEY` in the Render dashboard → Environment, to enable the LLM brain

**Railway** (alternative):

1. [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo** → pick this repo
2. Railway auto-detects the `Dockerfile` and deploys; open **Settings → Networking → Generate Domain**
3. (Optional) **+ New → Database → PostgreSQL**, then set `DATABASE_URL` to `${{Postgres.DATABASE_URL}}` (driver included, just works)

> **Free-tier notes:** Render's free service sleeps after inactivity — first visit takes ~30–60s to wake up. The demo uses SQLite, so data resets on redeploy and the app **auto-seeds a fresh demo** every time — ideal for client trials. For persistence, attach managed Postgres and set `DATABASE_URL`.

### Demo accounts

| Role | Email | Password | Notes |
|---|---|---|---|
| 👤 Customer | `demo@quicksave.io` | `demo1234` | 2 accounts, 90 days of realistic history |
| 🛡️ Admin | `admin@quicksave.io` | `admin1234` | Unlocks the Admin console |
| 💸 Transfer target | `QS1000000003` | — | Alex Carter — try sending money here |

New sign-ups get a **$100 welcome bonus** checking account automatically. 🎉

---

## 🖥️ What's inside

### Customer app
- 📊 **Dashboard** — total balance (animated), monthly income/expenses, cash-flow + category charts, recent activity
- 💳 **Accounts** — open savings/checking accounts, deposit, withdraw, per-account history
- 🧾 **Transactions** — cross-account search, type/category filters, pagination, **CSV export**
- 💸 **Transfers** — recipient verification preview, instant atomic settlement, receipt modal
- ✨ **AI Insights** — savings rate, top categories, anomaly detection, generated narrative
- 💬 **AI chat widget** — floating assistant on every screen, grounded in *your* real balances

### Admin console (`admin@quicksave.io`)
- Platform stats (users, accounts, deposits, 7-day volume)
- Account directory with **freeze / unfreeze** controls (frozen accounts block all mutations)
- User directory + live platform activity feed

### API (auto docs at `/docs`)
`POST /api/v1/auth/register` · `POST /api/v1/auth/login` · `GET /api/v1/users/me/summary`
`GET|POST /api/v1/accounts` · `POST /api/v1/accounts/{id}/deposit|withdraw`
`GET /api/v1/accounts/lookup/{number}` · `POST /api/v1/transactions/transfer`
`POST /api/v1/ai/chat` · `GET /api/v1/ai/insights` · `POST /api/v1/ai/categorize`
`GET /api/v1/admin/stats|users|accounts|transactions` · `PATCH /api/v1/admin/accounts/{id}/status`

---

## 🤖 AI / LLM integration (the interesting part)

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Web UI /   │────▶│  FastAPI AI layer    │────▶│ OpenAI-compatible   │
│  API client │◀────│  ai_service.py       │◀────│ LLM (if key set)    │
└─────────────┘     └──────────────────────┘     └─────────────────────┘
                              │ fallback (no key / LLM error)
                              ▼
                    ┌──────────────────────┐
                    │ Rule-based engine    │
                    │ grounded in live SQL │
                    └──────────────────────┘
```

- **Grounded answers** — the LLM receives a live snapshot (balances, 60-day income/expenses,
  top categories, recent transactions) as context; the fallback computes answers from the same data.
- **Graceful degradation** — any LLM failure automatically falls back to the local engine.
  Clients can demo the AI with **zero configuration**.
- **Plug in any model** — set two env vars and it uses your provider:
  ```bash
  OPENAI_API_KEY=sk-...            # or any compatible key
  OPENAI_BASE_URL=https://api.openai.com/v1   # Ollama: http://localhost:11434/v1
  OPENAI_MODEL=gpt-4o-mini         # e.g. llama3.1 for Ollama
  ```
- **Transaction auto-categorization** on every deposit/withdrawal/transfer.

---

## 🏗️ Project structure

```
QuickSave-Banking-System/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app: API + docs + serves the SPA
│   │   ├── core/                # config (pydantic-settings), JWT+bcrypt, auth deps
│   │   ├── db/                  # engine/session, bootstrap + deterministic seeder
│   │   ├── models/              # User, Account, Transaction (SQLAlchemy 2.0)
│   │   ├── schemas/             # Pydantic v2 request/response contracts
│   │   ├── api/v1/              # auth, users, accounts, transactions, ai, admin
│   │   └── services/            # banking.py (atomic ops) · ai_service.py (LLM+fallback)
│   ├── tests/                   # 14 end-to-end tests (pytest + TestClient)
│   └── Dockerfile
├── frontend/                    # dependency-free SPA: index.html + app.js + styles.css
├── docker-compose.yml
├── .env.example                 # DATABASE_URL, SECRET_KEY, OPENAI_* …
└── .github/workflows/ci.yml     # install + pytest on every push
```

---

## ⚙️ Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./quicksave.db` | Zero-setup DB; swap for `postgresql+psycopg://…` in prod |
| `SECRET_KEY` | dev key | JWT signing — **change in production** |
| `SEED_DEMO_DATA` | `true` | Auto-seed demo users on first launch |
| `OPENAI_API_KEY` | *(empty = offline AI)* | Enables the LLM brain |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Point at OpenAI / Azure / Ollama / vLLM |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat + insights model |

```bash
cp .env.example .env   # then edit
```

## 🧪 Tests

```bash
pytest backend/tests -q     # 14 passed — auth, banking, transfers, admin, AI
```

Covers: registration bonus, deposits/withdrawals, insufficient-funds rejection,
atomic balanced transfers, self-transfer rejection, account isolation between users,
admin RBAC + freeze enforcement, AI chat/insights/categorization.

---

## 🗺️ Roadmap (easy extensions)

- Refresh tokens + password reset via email · Postgres + Alembic migrations
- Per-user LLM usage metering · PDF statements · Recurring transfers
- React Native / Flutter client against the same API

---

## 👨‍💻 Author

**Zain Gulzar** — Backend Developer · **Python, FastAPI & AI/LLM Integration**

⭐ Available for freelance projects — if you like this build, let's talk on Upwork.

*Like this project? A star helps clients find it.*
