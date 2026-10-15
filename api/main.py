from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db.database import create_tables
from api.routes import search, predict, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup: create DB tables if they don't exist."""
    create_tables()
    print("✅ Database tables ready")
    yield
    print("👋 Shutting down")


app = FastAPI(
    title="Price Comparison + Prediction Engine",
    description="Real-time price scraping, time-series forecasting, and deal scoring across Amazon & Flipkart",
    version="2.0.0",
    lifespan=lifespan,
)

# Allow React frontend (localhost:5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(search.router,  tags=["Search"])
app.include_router(predict.router, tags=["Prediction"])
app.include_router(alerts.router,  tags=["Alerts"])


@app.get("/")
def root():
    return {
        "message": "Price Comparison + Prediction Engine API",
        "docs":    "/docs",
        "version": "2.0.0",
    }
