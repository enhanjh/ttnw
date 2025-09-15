# Portfolio Manager Web Application Development Summary

This document summarizes the development steps taken to create the Portfolio Manager web application, including backend (FastAPI) and frontend (React) components, database setup, and core functionalities like portfolio management and backtesting.

## 1. Initial Development Plan

포트폴리오 수익률 관리 및 백테스팅 웹 프로그램 개발 계획:

*   **목표:** 사용자가 자신의 포트폴리오를 등록하고 수익률을 관리하며, 다양한 투자 전략을 과거 데이터에 기반하여 백테스팅할 수 있는 웹 기반 애플리케이션 개발.
*   **주요 기능:**
    *   **포트폴리오 관리:** 자산 추가/수정/삭제, 매수/매도 기록 관리, 현재 포트폴리오 가치 및 구성 비율 시각화, 기간별 수익률 등 성과 지표 계산 및 시각화.
    *   **백테스팅:** 사용자 정의 투자 전략 설정, 과거 금융 데이터 기반 전략 시뮬레이션, 백테스팅 결과 분석 및 시각화.
    *   **데이터 관리:** 주요 금융 자산의 과거 가격 데이터 수집 및 저장.
*   **기술 스택 (제안):**
    *   **프론트엔드:** React (JavaScript/TypeScript), Bootstrap CSS / Material Design, Chart.js / D3.js.
    *   **백엔드:** Python (FastAPI), Pandas / NumPy, yfinance, backtrader.
    *   **데이터베이스:** SQLite.
    *   **배포:** Docker, Nginx, Gunicorn.
*   **개발 단계:** 요구사항 상세화 및 설계 -> 데이터 수집 및 백엔드 핵심 로직 개발 -> 프론트엔드 개발 -> 통합 및 테스트 -> 배포 및 최적화.

## 2. Project Setup

### Directory Structure
```
portfolio_manager/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── data_collector.py
│   ├── portfolio_calculator.py
│   ├── backtesting_engine.py
│   └── create_db.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── index.js
│   │   ├── components/
│   │   │   ├── Assets.js
│   │   │   ├── Transactions.js
│   │   │   └── Backtest.js
│   │   └── ... (other React files)
│   └── package.json
├── venv/
└── requirements.txt
```

### Commands Executed

*   **Create Project Directory & Python Virtual Environment (Python 3.12):**
    ```bash
    mkdir portfolio_manager && cd portfolio_manager && python3.12 -m venv venv && source venv/bin/activate && pip install --upgrade pip
    ```
*   **Install Backend Python Libraries:**
    ```bash
    cd portfolio_manager && echo "fastapi==0.111.0\nuvicorn==0.30.1\npandas==2.2.2\nnumpy==1.26.4\npsycopg2-binary==2.9.9\nSQLAlchemy==2.0.30\nyfinance==0.2.40" > requirements.txt && ./venv/bin/pip install -r requirements.txt
    ```
*   **Create React Project:**
    ```bash
    cd portfolio_manager && npx create-react-app frontend
    ```
*   **Install React Router DOM:**
    ```bash
    cd portfolio_manager/frontend && npm install react-router-dom
    ```
*   **Install Chart.js Libraries for React:**
    ```bash
    cd portfolio_manager/frontend && npm install react-chartjs-2 chart.js
    ```

## 3. Backend Development (FastAPI)

### Key Files and Purpose:

*   `backend/main.py`: Main FastAPI application, defines API endpoints for assets, transactions, data collection, and backtesting.
*   `backend/database.py`: SQLAlchemy setup for connecting to SQLite, defines `engine`, `SessionLocal`, and `Base`.
*   `backend/models.py`: SQLAlchemy ORM models for `Asset`, `Transaction`, and `Portfolio` tables.
*   `backend/schemas.py`: Pydantic schemas for request/response validation and serialization.
*   `backend/data_collector.py`: Contains `get_stock_data` function using `yfinance` to fetch historical stock data.
*   `backend/portfolio_calculator.py`: Implements functions to calculate portfolio value, returns, volatility, and max drawdown.
*   `backend/backtesting_engine.py`: Core backtesting logic, including `BacktestingEngine` class and an example `buy_and_hold_strategy`.
*   `backend/create_db.py`: Script to create database tables based on `models.py`.
*   `backend/__init__.py`: Makes `backend` a Python package.

### Running the Backend:

*   **SQLite Setup:**
    *Note: The SQLite database file `portfolio.db` will be created in the `portfolio_manager` directory when `create_db.py` is run.*
*   **Create Database Tables:**
    ```bash
    cd portfolio_manager && ./venv/bin/python -m backend.create_db
    ```
*   **Start FastAPI Server:**
    ```bash
    cd portfolio_manager/backend && ../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &
    ```
    *To stop the server (if allowed by your environment): `kill $(lsof -t -i:8000)`*

## 4. Frontend Development (React)

### Key Files and Purpose:

*   `frontend/src/App.js`: Main React application, sets up routing using `react-router-dom` for Home, Assets, Transactions, and Backtest pages.
*   `frontend/src/components/Assets.js`: Component for adding and viewing assets, interacts with `/assets/` API.
*   `frontend/src/components/Transactions.js`: Component for adding and viewing transactions, interacts with `/transactions/` API.
*   `frontend/src/components/Backtest.js`: Component for running backtests and displaying results, including a Chart.js visualization for portfolio value. Interacts with `/backtest/buy_and_hold` API.
*   `frontend/package.json`: Configures React project, includes `proxy` setting to forward API requests to the backend (`"proxy": "http://localhost:8000"`).

### Running the Frontend:

*   **Start React Development Server:**
    ```bash
    cd portfolio_manager/frontend && npm start &
    ```
    *To stop the server (if allowed by your environment): Find the process ID and kill it.*

## 5. Application Usage

1.  **Ensure database tables are created.**
2.  **Start the FastAPI backend server.**
3.  **Start the React frontend development server.**
4.  **Open your web browser and navigate to `http://localhost:3000`.**
5.  **Use the navigation links:**
    *   **Assets:** Add new assets (e.g., `AAPL`, `MSFT`).
    *   **Transactions:** Record buy/sell transactions for your assets.
    *   **Backtest:** Run a "Buy & Hold" backtest by providing symbols, date range, and initial capital. View the results, including the portfolio value chart.

## 6. Further Enhancements (Future Work)

*   Implement more sophisticated backtesting strategies.
*   Enhance data visualization with more chart types and interactive features.
*   Add user authentication and portfolio management per user.
*   Integrate with more real-time data sources.
*   Implement portfolio optimization algorithms.
