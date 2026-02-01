
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import asyncio
from typing import List
import os
from .monitor import manager

app = FastAPI()

# Pydantic model for input
class WebsiteInput(BaseModel):
    url: HttpUrl

# Serve static files for frontend
# Ensure the frontend directory exists relative to this file
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if not os.path.exists(frontend_path):
    os.makedirs(frontend_path)

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.on_event("startup")
async def startup_event():
    # Start the monitoring loop in the background
    asyncio.create_task(manager.monitor_loop())

@app.get("/")
async def get_dashboard():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.post("/api/websites")
async def add_website(website: WebsiteInput):
    success = manager.add_website(str(website.url))
    if not success:
        raise HTTPException(status_code=400, detail="Website already exists")
    await manager.notify_listeners()
    return {"message": "Website added"}

@app.get("/api/websites")
async def get_websites():
    return manager.get_all_websites()

@app.delete("/api/websites")
async def remove_website(website: WebsiteInput):
    success = manager.remove_website(str(website.url))
    if not success:
        raise HTTPException(status_code=404, detail="Website not found")
    await manager.notify_listeners()
    return {"message": "Website removed"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async def send_updates(data):
        await websocket.send_json(data)
    
    manager.add_listener(send_updates)
    
    try:
        # Send initial state
        await websocket.send_json(manager.get_all_websites())
        while True:
            # Keep connection open and handle potential client messages if needed
            # For now we just push updates
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.remove_listener(send_updates)
    except Exception as e:
        manager.remove_listener(send_updates)
        print(f"WebSocket error: {e}")
