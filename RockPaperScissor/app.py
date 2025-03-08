from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from RockPaperScissor.routes.game import game_router
from RockPaperScissor.routes.history import history_router
from RockPaperScissor.routes.stats import stats_router

# Initialize FastAPI app
app = FastAPI(
    title="Rock Paper Scissors AI API",
    description="A serverless Rock Paper Scissors game with AI opponents",
    version="1.0.0"
)

# Add CORS middleware with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(game_router, prefix="/game", tags=["Game"])
app.include_router(history_router, prefix="/history", tags=["History"])
app.include_router(stats_router, prefix="/stats", tags=["Statistics"])

# AWS Lambda handler
handler = Mangum(app)