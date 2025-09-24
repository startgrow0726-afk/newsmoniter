# main.py - Application entry point
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers and other modules that need to be initialized
# from api.routers import feed, admin, company
# from storage.database import init_db
# from modules.scheduler import scheduler

app = FastAPI(
    title="NewsMonitor API",
    description="AI-based corporate news monitoring system",
    version="3.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.on_event("startup")
async def startup_event():
    print("Application startup...")
    # await init_db()
    # scheduler.start()
    print("Application started.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutdown...")
    scheduler.shutdown()
    print("Scheduler stopped.")

# Include routers
app.include_router(feed.router, prefix="/feed", tags=["Feed"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
# app.include_router(admin.router, prefix="/admin", tags=["Admin"])
# app.include_router(company.router, prefix="/companies", tags=["Companies"])

@app.get("/")
def read_root():
    return {"message": "Welcome to NewsMonitor API v3"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# For development run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
 port=8000, reload=True)
00, reload=True)
