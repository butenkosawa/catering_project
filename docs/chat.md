

# Implementing "CateringGPT" (Chat to interact with the system)

- `HTTP POST /chat`
    - Request to create a session: `{"content": "Hey there! I would like to make an order."}`
    - Response: `{"content": "What do you want to order?", "session_id": 13}`
    - Request to add message: `{"content": "What do you have?", "session_id": 13}`
- `HTTP GET /chat/ID`
    - `[{}, {}, {}]`