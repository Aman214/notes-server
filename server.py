from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
# from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from y_py import YDoc
from fastapi.responses import JSONResponse

app = FastAPI()

# MongoDB connection
mongo_client = MongoClient("mongodb+srv://amanK:RghGhr%40123@clusternotes.jwcg8.mongodb.net/")
db = mongo_client["shared_notes"]
notes_collection = db["notes"]

# Keep track of connected clients
active_connections = []




class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: bytes):
        for connection in self.active_connections:
            try:
                await connection.send_bytes(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()


# @app.websocket("/ws/123")
# async def websocket_endpoint_for_talking(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             await websocket.send_text(f"Message text was: {data}")
#     except WebSocketDisconnect:
#         print("Client disconnected")
#     except Exception as e:
#         print(f"Error: {e}")

@app.websocket("/ws/{notesId}")
async def websocket_endpoint(websocket: WebSocket, notesId: str):

    # Connect the client
    await manager.connect(websocket)

    # Load or create the Y.js document
    doc_id = notesId
    ydoc = YDoc()

    # Load initial state from MongoDB
    existing_note = notes_collection.find_one({"_id": doc_id})
    if existing_note:
        with ydoc.begin_transaction() as txn:
            # Apply the update within a transaction
            txn.apply_update(existing_note["update"])

    #testing
    print("Connected to the websocket, for notesId: ", notesId, existing_note)

    try:
        while True:
            # # Receive CRDT update from the client
            # data = await websocket.receive_bytes()
            # ydoc.apply_update(data)

            # Receive CRDT update from the client
            message = await websocket.receive_bytes()
            with ydoc.begin_transaction() as txn:
                txn.apply_update(message)

            # Save the update to MongoDB
            update = ydoc.encode_state_as_update()
            await notes_collection.update_one(
                {"_id": doc_id},
                {"$set": {"update": update}},
                upsert=True,
            )

            # Broadcast the update to all connected clients
            await manager.broadcast(data)
    except WebSocketDisconnect:
        print("Client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")

@app.post("/handle_request")
async def handle_request(request: Request):
    data = await request.json()
    print(data, Request)
    notes_collection.insert_one({ "age": 21, "name": "Aman" })
    response_data = {
        "message": "Request received",
        "data": data,
    }
    return JSONResponse(content=response_data)
