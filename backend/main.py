from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
from database import trade_collection, daily_summary_collection
from models import DailySummaryModel
import asyncio

app = FastAPI(title="MT5 Tracker API")

# Allow CORS for the frontend Electron/Vue app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/api/history", response_model=List[DailySummaryModel])
async def get_history(account_id: str = None):
    """Retrieve historical daily summaries, optionally filtered by account."""
    summaries = []
    try:
        query = {"account_id": account_id} if account_id else {}
        cursor = daily_summary_collection.find(query).sort("date", -1)
        async for document in cursor:
            document['_id'] = str(document['_id'])
            summaries.append(DailySummaryModel(**document))
    except Exception as e:
        print(f"Database error during get_history: {e}")
    return summaries

@app.get("/api/accounts")
async def get_accounts():
    """Return distinct account IDs from the database."""
    try:
        accounts = await daily_summary_collection.distinct("account_id")
        return [a for a in accounts if a]  # Filter out empty strings
    except Exception as e:
        print(f"Database error during get_accounts: {e}")
        return []

@app.websocket("/ws/mt5")
async def mt5_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for MT5 script to push real-time trade updates.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Receive text data from MT5 script
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Here we could process different types of messages:
                # e.g., {'type': 'TRADE_CLOSED', 'data': {...}}
                # or {'type': 'DAILY_SUMMARY_UPDATE', 'data': {...}}

                if message.get("type") == "DAILY_SUMMARY_UPDATE":
                    summary_data = message.get("data")
                    # Upsert daily summary
                    date = summary_data.get("date")
                    timeframe = summary_data.get("timeframe", "Daily")
                    account_id = summary_data.get("account_id", "")
                    try:
                        await daily_summary_collection.update_one(
                            {"date": date, "timeframe": timeframe, "account_id": account_id},
                            {"$set": summary_data},
                            upsert=True
                        )
                    except Exception as e:
                        print(f"Database error during WS update: {e}. Skipping DB save.")
                    
                    # Broadcast update to connected frontend clients
                    await manager.broadcast(json.dumps({
                        "event": "update",
                        "data": summary_data
                    }))

                elif message.get("type") == "OPEN_POSITIONS_UPDATE":
                    positions_data = message.get("data")
                    account_id = message.get("account_id", "")
                    account_name = message.get("account_name", "")
                    broker = message.get("broker", "")
                    
                    # Broadcast positions to connected frontend clients
                    await manager.broadcast(json.dumps({
                        "event": "positions",
                        "data": positions_data,
                        "account_id": account_id,
                        "account_name": account_name,
                        "broker": broker
                    }))
            except json.JSONDecodeError:
                print("Failed to decode message.")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
