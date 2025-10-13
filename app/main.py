"""FastAPI application entry point for DemeterAI v2.0."""

from fastapi import FastAPI

app = FastAPI(
    title="DemeterAI v2.0",
    version="2.0.0",
    description="Automated plant counting and inventory management system",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
