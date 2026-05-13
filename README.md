# Real-Time Chat Application

## Features

- Mobile number login with mock OTP
- OTP saved in PostgreSQL
- JWT token after OTP verification
- Protected `/auth/me`
- Send message
- Fetch chat history
- Mark message as read
- Basic real-time events with Socket.IO

## Project Structure

```text
TASK/
├── src/
│   ├── auth.py
│   ├── main.py
│   ├── messages.py
│   ├── realtime.py
│   ├── schemas.py
│   └── db/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## Docker Setup

Start everything:

```bash
docker compose up --build -d
```

Check status:

```bash
docker compose ps
```

App logs:

```bash
docker compose logs -f app
```

Stop:

```bash
docker compose down
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Env Values

Auth settings are in:

- `.env`
- `.env.example`

Current values:

```env
OTP_EXPIRY_MINUTES=5
ACCESS_TOKEN_EXPIRE_MINUTES=60
SECRET_KEY=chat-app-secret
ALGORITHM=HS256
```

## API Endpoints

- `GET /health`
- `POST /auth/request-otp`
- `POST /auth/verify-otp`
- `GET /auth/me`
- `POST /messages`
- `GET /messages/{other_user_id}`
- `PATCH /messages/{message_id}/read`

## Auth Flow

Request OTP:

```bash
curl -X POST http://127.0.0.1:8000/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number":"9000000001"}'
```

Verify OTP:

```bash
curl -X POST http://127.0.0.1:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number":"9000000001","otp":"1234"}'
```

Get current user:

```bash
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer JWT_TOKEN"
```

## Message Flow

Send message:

```bash
curl -X POST http://127.0.0.1:8000/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer JWT_TOKEN" \
  -d '{"receiver_id":2,"message":"Hi from me"}'
```

Get history:

```bash
curl http://127.0.0.1:8000/messages/2 \
  -H "Authorization: Bearer JWT_TOKEN"
```

Mark as read:

```bash
curl -X PATCH http://127.0.0.1:8000/messages/MESSAGE_ID/read \
  -H "Authorization: Bearer JWT_TOKEN"
```

## Socket.IO Events

Client emits:

- `send_message`
- `mark_read`

Server emits:

- `message_sent`
- `receive_message`
- `message_read`

Connect with token:

```python
client.connect("http://127.0.0.1:8000", auth={"token": "JWT_TOKEN"})
```

## Tests

Run tests:

```bash
python -m pytest -q
```

Current tests cover:

- request and verify OTP
- wrong OTP rejection
- send message and fetch history
- mark message as read
