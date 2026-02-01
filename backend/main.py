
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
import asyncio
from typing import List
import os
import json
import csv
import io
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor import manager

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

@app.get("/api/statistics")
async def get_statistics():
    """Get overall statistics for all monitored websites"""
    websites = manager.get_all_websites()
    
    if not websites:
        return {
            "total_websites": 0,
            "websites_up": 0,
            "websites_down": 0,
            "average_uptime": 0,
            "average_response_time": 0,
            "total_checks": 0
        }
    
    total_websites = len(websites)
    websites_up = sum(1 for w in websites if w["is_up"])
    websites_down = total_websites - websites_up
    average_uptime = sum(w["uptime_percentage"] for w in websites) / total_websites
    
    # Calculate average response time for sites that are up
    response_times = [w["avg_response_time"] for w in websites if w["avg_response_time"] > 0]
    average_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    total_checks = sum(w["total_checks"] for w in websites)
    
    return {
        "total_websites": total_websites,
        "websites_up": websites_up,
        "websites_down": websites_down,
        "average_uptime": round(average_uptime, 2),
        "average_response_time": round(average_response_time, 2),
        "total_checks": total_checks
    }

@app.get("/api/export/json")
async def export_json():
    """Export all monitoring data as JSON"""
    data = manager.get_all_websites()
    json_str = json.dumps(data, indent=2)
    
    return StreamingResponse(
        iter([json_str]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=website-status-export.json"}
    )

@app.get("/api/export/csv")
async def export_csv():
    """Export monitoring data as CSV"""
    websites = manager.get_all_websites()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "URL", "Status", "Is Up", "Response Time (ms)", 
        "Avg Response Time (ms)", "Uptime %", "Total Checks", 
        "Last Checked", "Created At"
    ])
    
    # Write data
    for site in websites:
        writer.writerow([
            site["url"],
            site["status"],
            site["is_up"],
            site["response_time"],
            site["avg_response_time"],
            site["uptime_percentage"],
            site["total_checks"],
            site["last_checked"],
            site["created_at"]
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=website-status-export.csv"}
    )

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
