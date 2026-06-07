from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import inbound, outbound

app = FastAPI(title="AI Voice Engine Orchestrator")

# Create database tables automatically for development scale
try:
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables initialized")
except Exception as e:
    print(f"⚠ Database not available yet: {e}")
    print("  Tables will be created on first successful connection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inbound.router, prefix="/api/v1/inbound", tags=["Inbound Flows"])
app.include_router(outbound.router, prefix="/api/v1/outbound", tags=["Outbound Flows"])

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "voice-engine"}
