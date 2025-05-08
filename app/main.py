"""
Main application entry point for the GenAI Research Assistant API.
This file initializes the FastAPI application, configures CORS middleware, 
includes API routers, and sets up database initialization on startup.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.database import create_db_and_tables

app = FastAPI(
    title="GenAI Research Assistant API",
    description="Backend API for the GenAI Research Assistant",
    version="0.1.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    # Create database tables on startup
    await create_db_and_tables()

@app.get("/")
async def root():
    return {"message": "Welcome to the GenAI Research Assistant API"}