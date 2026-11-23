# PTV Investing — Master Architecture & Roadmap

> **Purpose:** Living blueprint for building, running, and scaling the PTV Investing platform over the next 5+ years—starting locally on Windows and migrating cleanly to Linux and Google Cloud.

---

## 1. Long-Term Vision
1. **Custom Stock Charting:** Detailed, StockCharts.com-inspired interactive charting tailored to proprietary workflows, overlays, indicators, and saved chart styles.
2. **Financial Analysis & SEC Reports:** Automated ingestion of Schwab stock/options data and SEC EDGAR filings to power deep financial analysis and downloadable/sellable reports.
3. **Website, Blog & Commercial Service:** Public marketing site, SEO-friendly blog, user authentication, and paid subscriptions/report sales hosted on Google Cloud.

---

## 2. Locked-In Technology Stack
Designed for **zero rewrites** from local Windows development to Linux/Cloud production, with **strict static typing** on both backend and frontend.

| Layer | Technology | Why |
| :--- | :--- | :--- |
| **Backend API & Analysis** | **Python 3.13 + FastAPI + Pydantic** | Best ecosystem for Schwab APIs, SEC EDGAR/XBRL, technical indicators, options math, and PDF reports; strict type hints + `pyright`/`mypy` + `pytest`. |
| **Analytics & Data Storage** | **DuckDB** (local analytics) → **PostgreSQL / TimescaleDB** (cloud) | Zero-config fast time-series/SQL on Windows; clean migration path to Google Cloud SQL. |
| **Frontend, Charts & Blog** | **TypeScript (`strict: true`) + Next.js (React)** | Runs in the browser locally (`localhost`) on Windows and deploys identically to Linux/Cloud. Handles charting, dashboards, blog (MDX), and checkout in one codebase. |
| **Charting Engine** | **TradingView Lightweight Charts** | Open-source, high-performance Canvas charting supporting candlesticks, volume, overlays, multi-pane indicators, and custom extensions. |
| **Hosting (Future)** | **Google Cloud (Cloud Run + Cloud SQL + Cloud Storage)** | Containerized (Docker) Python + Next.js services; low idle cost, scales automatically. |

---

## 3. Phased Roadmap

### Phase 0: Workspace & Foundation
- [ ] Initialize Git repository in `c:\Dev\PTV-Investing` (`.gitignore`, clean folder structure: `backend/`, `frontend/`, `docs/`).
- [ ] Set up Python virtual environment + FastAPI skeleton + `pytest` + strict type checking.
- [ ] Set up Next.js + TypeScript skeleton (once Node.js LTS is installed on this machine or on the 128 GB workstation).

### Phase 1: Standalone Stock Charting App *(Current Focus)*
Build a clean, fast charting app first—with backend/frontend separation so nothing is thrown away later:
- [ ] **Market Data Provider Interface:** Abstract data-source interface so we can start with sample/public OHLCV data immediately and plug in Schwab seamlessly in Phase 2.
- [ ] **Core Charting UI:** Symbol lookup, timeframes (intraday/daily/weekly/monthly), candlestick/OHLC/line views, volume pane, crosshair & zoom/pan.
- [ ] **Indicators & Overlays:** Moving averages (SMA/EMA), Bollinger Bands, RSI, MACD, plus custom proprietary indicators.
- [ ] **Saved Chart Styles & Watchlists:** Save/load user layouts, indicator presets, and watchlists locally.

### Phase 2: Schwab Data & Options Integration
- [ ] Resurrect Schwab developer OAuth2 authentication and token refresh flow.
- [ ] Live/historical stock price bars and quote endpoints.
- [ ] Options chain ingestion, Greeks/IV calculations, and options analysis views.

### Phase 3: SEC EDGAR & Financial Analysis Reports
- [ ] Automated SEC EDGAR filing & XBRL financial statement ingestion.
- [ ] Custom financial analysis models (ratios, historical trends, valuation, screening).
- [ ] Automated, branded **PDF / web report generation** ready to sell to subscribers.

### Phase 4: Website, Blog & Google Cloud Launch
- [ ] Public landing pages and **MDX/CMS Blog**.
- [ ] User accounts, authentication, and **Stripe** subscriptions / single-report purchases.
- [ ] Dockerize `backend/` and `frontend/`, migrate data store to PostgreSQL + Cloud Storage, and deploy to **Google Cloud (GCP)** on Linux.

---

## 4. Machine & Transition Notes
- **Current Machine:** Windows with Python 3.13.14, Git 2.54.0, and `winget` installed. Node.js LTS not yet installed.
- **Main Workstation (1–2 weeks):** 128 GB RAM rig. Everything built here in Git will transfer cleanly via `git clone` or copying `c:\Dev\PTV-Investing`.

---

## 5. Next Session Checklist (When Ready)
1. Define your **Phase 1 Charting Wishlist** (must-have indicators, chart layout/panes, timeframes, and any StockCharts.com habits you want to keep or improve).
2. Decide whether to:
   - Start building the **Python `backend/`** right now (no extra installs needed), or
   - Install **Node.js LTS** here so we can preview the chart in your browser right away.
