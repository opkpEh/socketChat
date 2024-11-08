import socket
import json
import sys
import threading
import readline
import random
import uuid
from datetime import datetime
from typing import Optional, Set
import time


class ChatClient:
    COLORS = {
        'red': '\033[91m',
        'blue': '\033[94m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'white': '\033[97m',
        'purple': '\033[95m',
        'cyan': '\033[96m'
    }
    RESET = '\033[0m'

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.connected = False
        self.receive_thread = None
        self.send_thread = None
        self.typing_thread = None
        self.current_input = ""
        self.lock = threading.Lock()
        self.color = random.choice(list(self.COLORS.keys()))
        self.known_users: Set[str] = set()
        self.is_typing = False
        self.last_typing_status = False
        self.unacked_messages = {}

        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.username_completer)

    def username_completer(self, text: str, state: int) -> Optional[str]:
        if text.startswith('@'):
            text = text[1:]
            matches = [f'@{u}' for u in self.known_users if u.startswith(text)]
        else:
            matches = [u for u in self.known_users if u.startswith(text)]

        return matches[state] if state < len(matches) else None

    def clear_current_line(self):
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()

    def remake_input_line(self):
        sys.stdout.write(f'\r> {self.current_input}')
        sys.stdout.flush()

    def show_help(self):
        help_text = """
Available Commands:
/help     - Shows help messages
/quit     - Ceave chat
/users    - All active users
/clear    - Clear the screen
/color    - Change your color 
/dm <user> <message> - Send a direct message (alternative to @user)
/exclude <user> <message> - Exclude a user from seeing a message (alternative to !user)

Special Message Prefixes:
@username - Send a direct message to a user
!username - Send a message that excludes a specific user
        """
        print(help_text)

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f'Connected to {self.host}:{self.port}')
            return True
        except ConnectionRefusedError:
            print("Could not connect to server. Is it running?")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def format_message(self, message):
        timestamp = datetime.fromisoformat(message.get('timestamp', datetime.now().isoformat()))
        time_str = timestamp.strftime("%H:%M:%S")

        if message.get('type') == 'system':
            return f"[{time_str}] [System] {message['message']}"
        elif message.get('type') == 'typing':
            username = message.get('username', 'Unknown')
            is_typing = message.get('is_typing', False)
            return f"{username} is {'typing...' if is_typing else 'stopped typing'}"
        else:
            sender = message.get('username', 'Unknown')
            content = message.get('message', '')
            msg_color = self.COLORS.get(message.get('color', 'white'))

            prefix = ""
            if message.get('type') == 'direct':
                prefix = "(DM) "
            elif message.get('type') == 'excluded':
                prefix = "(Excluded) "

            return f"[{time_str}] {msg_color}{sender}: {prefix}{content}{self.RESET}"

    def receive_message(self) -> bool:
        try:
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                raise ConnectionError("Server closed connection")

            message_length = int.from_bytes(length_bytes, 'big')

            message_data = b''
            while len(message_data) < message_length:
                remaining = message_length - len(message_data)
                chunk = self.socket.recv(min(remaining, 1024))
                if not chunk:
                    raise ConnectionError("Connection broken while receiving message")
                message_data += chunk

            message = json.loads(message_data.decode())

            if message.get('type') == 'ack':
                message_id = message.get('message_id')
                if message_id in self.unacked_messages:
                    del self.unacked_messages[message_id]
                return True

            if message.get('username'):
                self.known_users.add(message.get('username'))

            with self.lock:
                self.clear_current_line()
                formatted_message = self.format_message(message)
                print(formatted_message)
                self.remake_input_line()

            if message.get('id'):
                self.acknowledge_message(message.get('id'))

            return True

        except ConnectionError as e:
            print(f"\nDisconnected from server: {e}")
            self.connected = False
            return False
        except json.JSONDecodeError:
            print("\nReceived invalid message format")
            return True
        except Exception as e:
            print(f"\nError receiving message: {e}")
            self.connected = False
            return False

    def validate_target_user(self, target_user: str) -> bool:
        if not target_user:
            print("Invalid username specified")
            return False
        if target_user == self.username:
            print("You cannot target yourself")
            return False
        if target_user not in self.known_users:
            print(f"Warning: User '{target_user}' has not been seen in the chat")
        return True

    def process_command(self, message: str) -> bool:
        if not message.startswith('/'):
            return False

        parts = message.split(maxsplit=2)
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == '/quit':
            self.connected = False
            return True
        elif command == '/help':
            self.show_help()
            return True
        elif command == '/users':
            print("Online users:", ", ".join(sorted(self.known_users)))
            return True
        elif command == '/clear':
            print("\033[H\033[J", end="")
            return True
        elif command == '/color':
            self.color = random.choice(list(self.COLORS.keys()))
            print(f"Changed color to {self.color}")
            return True
        elif command == '/dm' and len(args) >= 2:
            target_user = args[0]
            message_content = args[1]
            if self.validate_target_user(target_user):
                self.send_message(f"@{target_user} {message_content}")
            return True
        elif command == '/exclude' and len(args) >= 2:
            target_user = args[0]
            message_content = args[1]
            if self.validate_target_user(target_user):
                self.send_message(f"!{target_user} {message_content}")
            return True

        print(f"Unknown command: {command}")
        return True

    def process_outgoing_message(self, message: str) -> dict:
        msg_type = "message"
        target_user = None
        excluded_user = None

        if message.startswith('@'):
            parts = message.split(' ', 1)
            if len(parts) > 1:
                target_user = parts[0][1:]
                if self.validate_target_user(target_user):
                    message = parts[1]
                    msg_type = "direct"
                else:
                    return None

        elif message.startswith('!'):
            parts = message.split(' ', 1)
            if len(parts) > 1:
                excluded_user = parts[0][1:]
                if self.validate_target_user(excluded_user):
                    message = parts[1]
                    msg_type = "excluded"
                else:
                    return None

        message_id = str(uuid.uuid4())
        return {
            "id": message_id,
            "type": msg_type,
            "username": self.username,
            "message": message,
            "color": self.color,
            "timestamp": datetime.now().isoformat(),
            "target_user": target_user,
            "excluded_user": excluded_user
        }

    def send_message(self, message: str) -> bool:
        try:
            data = self.process_outgoing_message(message)
            if not data:
                return True

            json_data = json.dumps(data).encode()
            message_length = len(json_data)
            self.socket.send(message_length.to_bytes(4, 'big'))
            self.socket.send(json_data)

            self.unacked_messages[data['id']] = data

            return True

        except Exception as e:
            print(f"\nError sending message: {e}")
            self.connected = False
            return False

    def acknowledge_message(self, message_id: str):
        try:
            ack_data = {
                "type": "ack",
                "message_id": message_id,
                "username": self.username
            }
            json_data = json.dumps(ack_data).encode()
            message_length = len(json_data)
            self.socket.send(message_length.to_bytes(4, 'big'))
            self.socket.send(json_data)
        except Exception as e:
            print(f"\nError sending acknowledgment: {e}")

    def update_typing_status(self):
        while self.connected:
            if self.is_typing != self.last_typing_status:
                try:
                    data = {
                        "type": "typing",
                        "username": self.username,
                        "is_typing": self.is_typing
                    }
                    json_data = json.dumps(data).encode()
                    message_length = len(json_data)
                    self.socket.send(message_length.to_bytes(4, 'big'))
                    self.socket.send(json_data)
                    self.last_typing_status = self.is_typing
                except Exception:
                    pass
            time.sleep(0.5)

    def receive_loop(self):
        while self.connected:
            if not self.receive_message():
                break
        self.cleanup()

    def send_loop(self):
        while self.connected:
            try:
                self.current_input = input("> ")
                self.is_typing = False

                if self.current_input.strip():
                    with self.lock:
                        if not self.process_command(self.current_input):
                            if not self.send_message(self.current_input):
                                break
                self.current_input = ""
            except KeyboardInterrupt:
                print("\nExiting...")
                self.connected = False
                break
            except EOFError:
                break
        self.cleanup()

    def cleanup(self):
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def start(self):
        if not self.connect():
            return

        self.username = input("Enter your username: ").strip()
        while not self.username:
            print("Username cannot be empty")
            self.username = input("Enter your username: ").strip()

        join_message = {
            "type": "join",
            "username": self.username,
            "message": "",
            "color": self.color,
            "timestamp": datetime.now().isoformat()
        }
        json_data = json.dumps(join_message).encode()
        self.socket.send(len(json_data).to_bytes(4, 'big'))
        self.socket.send(json_data)

        self.receive_thread = threading.Thread(target=self.receive_loop)
        self.send_thread = threading.Thread(target=self.send_loop)
        self.typing_thread = threading.Thread(target=self.update_typing_status)

        self.receive_thread.daemon = True
        self.send_thread.daemon = True
        self.typing_thread.daemon = True

        self.receive_thread.start()
        self.send_thread.start()
        self.typing_thread.start()

        try:
            self.send_thread.join()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.cleanup()


def main():
    client = ChatClient('127.0.0.1', 8080)
    client.start()


if __name__ == "__main__":
    main()