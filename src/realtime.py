from collections import defaultdict

import socketio

from src.auth import decode_access_token
from src.db import create_message, get_mongo_database, mark_message_as_read
from src.db.mongo import serialize_message

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
connected_users = defaultdict(set)
socket_user_map = {}

@sio.event
async def connect(sid, environ, auth):
    token = None
    if auth:
        token = auth.get("token")
    if not token:
        raise ConnectionRefusedError("Authentication token is required")
    user = decode_access_token(token)
    user_id = int(user["sub"])
    connected_users[user_id].add(sid)
    socket_user_map[sid] = user


@sio.event
async def disconnect(sid):
    user = socket_user_map.pop(sid, None)
    if not user:
        return
    user_id = int(user["sub"])
    connected_users[user_id].discard(sid)
    if not connected_users[user_id]:
        connected_users.pop(user_id, None)


@sio.event
async def send_message(sid, data):
    user = socket_user_map.get(sid)
    if not user:
        raise ConnectionRefusedError("User is not authenticated")
    mongo_db = get_mongo_database()

    try:

        msg = create_message(
            mongo_db,
            sender_id=int(user["sub"]),
            receiver_id=int(data["receiver_id"]),
            message=data["message"],)
    
    finally:
        mongo_db.client.close()

    msg_data = serialize_message(msg)
    
    await sio.emit("message_sent", msg_data, to=sid)

    for receiver_sid in connected_users.get(int(data["receiver_id"]), set()):
        await sio.emit("receive_message", msg_data, to=receiver_sid)


@sio.event
async def mark_read(sid, data):
    user = socket_user_map.get(sid)
    if not user:
        raise ConnectionRefusedError("User is not authenticated")
    mongo_db = get_mongo_database()

    try:

        msg = mark_message_as_read(
            mongo_db,
            message_id=data["message_id"],
            reader_id=int(user["sub"]),
        )

    finally:
        mongo_db.client.close()

    if not msg:
        return


    await sio.emit("message_read", msg, to=sid)
    for sender_sid in connected_users.get(int(msg["sender_id"]), set()):
        await sio.emit("message_read", msg, to=sender_sid)
