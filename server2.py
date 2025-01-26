from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pymongo import MongoClient
from typing import Dict

# Initialize FastAPI app and MongoDB client
app = FastAPI()

# mongo_client = MongoClient("mongodb+srv://amanK:RghGhr%40123@clusternotes.jwcg8.mongodb.net/")
# db = mongo_client["shared_notes"]
# documents_collection = db["notes"]


client = MongoClient("mongodb+srv://amanK:RghGhr%40123@clusternotes.jwcg8.mongodb.net/")
db = client["shared_notes"]
documents_collection = db["notes"]

default_value = ""

# Keep track of active WebSocket connections
active_connections: Dict[str, set] = {}

# Helper function to find or create a document
def find_or_create_document(document_id: str):
    if document_id is None:
        return None
    document = documents_collection.find_one({"_id": document_id})
    if document:
        return document
    documents_collection.insert_one({"_id": document_id, "data": default_value})
    return {"_id": document_id, "data": default_value}

# WebSocket endpoint
@app.websocket("/ws/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str):
    await websocket.accept()

    # Add client to the active connections
    if document_id not in active_connections:
        active_connections[document_id] = set()
    active_connections[document_id].add(websocket)

    try:
        # Load or create the document
        document = find_or_create_document(document_id)
        await websocket.send_json({"event": "load-document", "data": document["data"]})

        while True:
            data = await websocket.receive_json()
            
            # Handle "send-changes" event
            if data["event"] == "send-changes":
                delta = data["delta"]
                # Broadcast changes to all other clients
                for connection in active_connections[document_id]:
                    if connection != websocket:
                        await connection.send_json({"event": "receive-changes", "delta": delta})

            # Handle "save-document" event
            elif data["event"] == "save-document":
                updated_data = data["data"]
                documents_collection.update_one(
                    {"_id": document_id}, {"$set": {"data": updated_data}}
                )

    except WebSocketDisconnect:
        # Remove the client from active connections on disconnect
        active_connections[document_id].remove(websocket)
        if not active_connections[document_id]:
            del active_connections[document_id]

