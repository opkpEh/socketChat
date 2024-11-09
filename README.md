# Terminal Chat Application

A feature-rich terminal-based chat application built with Python, supporting multiple concurrent users, colored messages, and various chat commands. The application uses socket programming for real-time communication and SQLite for message persistence.

## Features

- 🌈 **Colored Messages**: Each user gets a random color for their messages
- 👥 **Multiple Users**: Support for concurrent chat sessions
- 📝 **Message History**: Recent messages are stored and loaded for new users
- 🔒 **Private Messaging**: Send direct messages to specific users
- 🚫 **Message Exclusion**: Send messages visible to all except specific users
- 💾 **Persistent Storage**: Chat history stored in SQLite database
- 🔄 **Chunked Messages**: Large messages are sent in chunks for better performance
- ⚡ **Non-blocking I/O**: Messages don't interrupt typing

## Requirements

```
sqlite3
readline
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/terminal-chat.git
cd terminal-chat
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

1. Run the server script:
```bash
python chat_server.py
```

The server will start listening on `localhost:8080` by default.

### Connecting as a Client

1. Run the client script:
```bash
python chat_client.py
```

2. Enter your username when prompted.

### Available Commands

| Command | Description |
|---------|-------------|
| `/help` | Shows all available commands |
| `/quit` | Leave the chat |
| `/users` | Display all active users |
| `/clear` | Clear the screen |
| `/color` | Change your message color randomly |
| `/dm <user> <message>` | Send a direct message |
| `/exclude <user> <message>` | Send a message excluding specific user |

### Special Message Prefixes

- `@username <message>`: Send a direct message to a specific user
- `!username <message>`: Send a message that excludes a specific user

## Technical Features

### Server-side
- Thread-safe client handling
- SQLite database for message persistence
- Graceful shutdown handling
- Message history management
- Broadcast and targeted message support

### Client-side
- Non-blocking message reception
- Username auto-completion
- Typing status indicators
- Message acknowledgment system
- Color-coded output
- Input line preservation during incoming messages

## Architecture

The application follows a client-server architecture:
- Server manages multiple client connections using threading
- Each client connection is handled in a separate thread
- Messages are sent with length prefixing for proper framing
- SQLite database maintains message history
- Mutex locks ensure thread-safe operations

## Error Handling

- Connection failures
- Disconnection handling
- Invalid message format handling
- Database transaction management
- Thread cleanup on exit

## Limitations

- Server runs on localhost by default
- Maximum message size is 1MB
- Stores last 20 messages in history
- No end-to-end encryption
- No file transfer support

## Contributing

Feel free to submit issues and enhancement requests!

## License

[MIT License](LICENSE)