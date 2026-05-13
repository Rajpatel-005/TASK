import os
from collections.abc import Generator
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import MongoClient


def get_mongo_database():
    client = MongoClient(
        host=os.getenv("MONGO_HOST", "localhost"),
        port=int(os.getenv("MONGO_PORT", "27017")),
        username=os.getenv("MONGO_USER", "mongo_user"),
        password=os.getenv("MONGO_PASSWORD", "mongo_password"),
    )
    database_name = os.getenv("MONGO_DB", "chat_messages")
    return client[database_name]


def get_mongo_db() -> Generator:
    database = get_mongo_database()
    try:
        yield database
    finally:
        database.client.close()


def get_messages_collection(database):
    return database["messages"]


def serialize_message(document: dict[str, object]) -> dict[str, object]:
    serialized_document = dict(document)
    object_id = serialized_document.pop("_id", None)
    if object_id is not None:
        serialized_document["id"] = str(object_id)
    timestamp = serialized_document.get("timestamp")
    if isinstance(timestamp, datetime):
        serialized_document["timestamp"] = timestamp.isoformat()
    return serialized_document


def create_message(database, sender_id: int, receiver_id: int, message: str):
    document = {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "message": message,
        "timestamp": datetime.now(timezone.utc),
        "is_read": False,
    }
    get_messages_collection(database).insert_one(document)
    return document


def get_chat_history(database, user_id: int, other_user_id: int):
    cursor = get_messages_collection(database).find(
        {
            "$or": [
                {"sender_id": user_id, "receiver_id": other_user_id},
                {"sender_id": other_user_id, "receiver_id": user_id},
            ]
        },
    ).sort("timestamp", 1)
    return [serialize_message(message) for message in cursor]


def mark_message_as_read(database, message_id: str, reader_id: int):
    if not ObjectId.is_valid(message_id):
        return None

    collection = get_messages_collection(database)
    collection.update_one(
        {"_id": ObjectId(message_id), "receiver_id": reader_id},
        {"$set": {"is_read": True}},
    )
    document = collection.find_one({"_id": ObjectId(message_id)})
    if not document:
        return None
    return serialize_message(document)
