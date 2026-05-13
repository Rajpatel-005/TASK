from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

import src.main as main_module
import src.messages as messages_module
from src.main import fastapi_app


def make_messages_client(monkeypatch):
    state = {"messages": []}

    def fake_initialize_postgres_tables():
        return None

    def fake_get_mongo_db():
        yield state

    def fake_get_current_user():
        return {"sub": "10", "mobile_number": "9537448304"}

    def fake_create_message(database, sender_id, receiver_id, message):
        document = {
            "_id": ObjectId(),
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "is_read": False,
        }
        database["messages"].append(document)
        return document

    def fake_get_chat_history(database, user_id, other_user_id):
        matched_messages = []
        for message in database["messages"]:
            if (
                message["sender_id"] == user_id
                and message["receiver_id"] == other_user_id
            ) or (
                message["sender_id"] == other_user_id
                and message["receiver_id"] == user_id
            ):
                matched_messages.append(messages_module.serialize_message(message))
        return matched_messages

    def fake_mark_message_as_read(database, message_id, reader_id):
        for message in database["messages"]:
            if str(message["_id"]) == message_id and message["receiver_id"] == reader_id:
                message["is_read"] = True
                return messages_module.serialize_message(message)
        return None

    monkeypatch.setattr(main_module, "initialize_postgres_tables", fake_initialize_postgres_tables)
    monkeypatch.setattr(messages_module, "create_message", fake_create_message)
    monkeypatch.setattr(messages_module, "get_chat_history", fake_get_chat_history)
    monkeypatch.setattr(messages_module, "mark_message_as_read", fake_mark_message_as_read)
    fastapi_app.dependency_overrides[messages_module.get_mongo_db] = fake_get_mongo_db
    fastapi_app.dependency_overrides[messages_module.get_current_user] = fake_get_current_user

    client = TestClient(fastapi_app)
    return client, state


def test_send_message_and_get_history(monkeypatch):
    client, _ = make_messages_client(monkeypatch)

    send_response = client.post(
        "/messages",
        json={"receiver_id": 11, "message": "Hi from me"},
    )
    assert send_response.status_code == 200
    sent_data = send_response.json()["data"]
    assert sent_data["message"] == "Hi from me"
    assert sent_data["is_read"] is False

    history_response = client.get("/messages/11")
    assert history_response.status_code == 200
    history = history_response.json()["messages"]
    assert len(history) == 1
    assert history[0]["message"] == "Hi from me"

    client.close()
    fastapi_app.dependency_overrides.clear()


def test_mark_message_as_read(monkeypatch):
    client, state = make_messages_client(monkeypatch)

    send_response = client.post(
        "/messages",
        json={"receiver_id": 10, "message": "Reply to me"},
    )
    message_id = send_response.json()["data"]["id"]

    state["messages"][0]["receiver_id"] = 10

    read_response = client.patch(f"/messages/{message_id}/read")
    assert read_response.status_code == 200
    assert read_response.json()["data"]["is_read"] is True

    client.close()
    fastapi_app.dependency_overrides.clear()
