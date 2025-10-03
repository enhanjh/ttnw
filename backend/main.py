import os
from fastapi import FastAPI
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, close_db
from .api import auth, portfolios, assets, transactions, strategies, backtesting, data, market_data

app = FastAPI(title="ttnw-api")

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.on_event("shutdown")
async def on_shutdown():
    close_db()

FRONTEND_URL = os.getenv("REACT_APP_FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

app.include_router(auth.router)
app.include_router(portfolios.router)
app.include_router(assets.router)
app.include_router(transactions.router)
app.include_router(strategies.router)
app.include_router(backtesting.router)
app.include_router(data.router)
app.include_router(market_data.router)

handler = Mangum(app)