import socket
import json
import threading
import signal
import time
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime


class ChatServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: Dict[socket.socket, str] = {}
        self.clients_lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.accept_thread = None
        self.message_history: List[dict] = []
        self.setup_database(self)
        self.load_recent_messages()
        self.colors = {
            'red': '\033[91m',
            'blue': '\033[94m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'white': '\033[97m',
            'purple': '\033[95m',
            'cyan': '\033[96m'
        }
    @staticmethod
    def setup_database(self):
        with sqlite3.connect('chat_history.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    target_user TEXT,
                    color TEXT,
                    excluded_user TEXT
                )
            ''')
            conn.commit()

    def load_recent_messages(self):
        with sqlite3.connect('chat_history.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, username, message, message_type, target_user, color, excluded_user
                FROM messages 
                ORDER BY id DESC LIMIT 20
            ''')
            rows = cursor.fetchall()

            for row in reversed(rows):
                message_data = {
                    "timestamp": row[0],
                    "username": row[1],
                    "message": row[2],
                    "type": row[3],
                    "target_user": row[4],
                    "color": row[5],
                    "excluded_user": row[6]
                }
                self.message_history.append(message_data)

    @staticmethod
    def save_message(message_data: dict):
        with sqlite3.connect('chat_history.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (
                    timestamp, username, message, message_type, 
                    target_user, color, excluded_user
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                message_data.get('username', ''),
                message_data.get('message', ''),
                message_data.get('type', 'message'),
                message_data.get('target_user'),
                message_data.get('color'),
                message_data.get('excluded_user')
            ))
            conn.commit()

    def handle_command(self, client_socket: socket.socket, message_data: dict) -> tuple[
        dict, Optional[str], Optional[str]]:
        message = message_data.get('message', '')
        username = message_data.get('username', '')
        parts = message.split(maxsplit=2)
        command = parts[0].lower()

        if command == '/quit':
            raise ConnectionError("Client requested disconnect")

        elif command == '/users':
            with self.clients_lock:
                active_users = list(self.clients.values())
            system_message = {
                "type": "system",
                "message": f"Active users: {', '.join(sorted(active_users))}",
                "timestamp": datetime.now().isoformat()
            }
            self._send_message(client_socket, system_message)
            return None, None, None

        elif command == '/color':
            new_color = message_data.get('color', 'white')
            system_message = {
                "type": "system",
                "message": f"{username} changed their color to {new_color}",
                "timestamp": datetime.now().isoformat()
            }
            self.broadcast(system_message)
            return None, None, None

        elif command == '/dm' and len(parts) >= 3:
            target_user = parts[1]
            content = parts[2]
            message_data['type'] = 'direct'
            message_data['message'] = content
            message_data['target_user'] = target_user
            return message_data, target_user, None

        elif command == '/exclude' and len(parts) >= 3:
            excluded_user = parts[1]
            content = parts[2]
            message_data['type'] = 'excluded'
            message_data['message'] = content
            message_data['excluded_user'] = excluded_user
            return message_data, None, excluded_user

        return self.process_message(message_data)

    @staticmethod
    def process_message(message_data: dict) -> tuple[dict, Optional[str], Optional[str]]:
        message = message_data.get('message', '')
        target_user = None
        excluded_user = None

        if message.startswith('@'):
            parts = message.split(' ', 1)
            if len(parts) > 1:
                target_user = parts[0][1:]
                message = parts[1]
                message_data['type'] = 'direct'
                message_data['target_user'] = target_user

        elif message.startswith('!'):
            parts = message.split(' ', 1)
            if len(parts) > 1:
                excluded_user = parts[0][1:]
                message = parts[1]
                message_data['type'] = 'excluded'
                message_data['excluded_user'] = excluded_user

        message_data['message'] = message
        return message_data, target_user, excluded_user

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"Server listening on {self.host}:{self.port}")
        self.accept_thread = threading.Thread(target=self.accept_connections)
        self.accept_thread.start()

    def accept_connections(self):
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"New connection from {client_address}")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")

    def broadcast(self, message: dict, sender_socket: socket.socket = None,
                  target_user: str = None, excluded_user: str = None):
        with self.clients_lock:
            disconnected_clients = []
            sender_username = self.clients.get(sender_socket, '')

            for client_socket, username in self.clients.items():
                should_send= False

                if message.get('type') == 'direct' and target_user:
                    should_send = (username == target_user or username == sender_username)
                elif message.get('type') == 'excluded' and excluded_user:
                    should_send = (username != excluded_user)
                else:
                    should_send = (client_socket != sender_socket)

                if should_send:
                    try:
                        if (message.get('type') == 'direct' and
                                username not in [target_user, sender_username]):
                            continue
                        self._send_message(client_socket, message)
                    except Exception as e:
                        print(f"Error broadcasting to client {username}: {e}")
                        disconnected_clients.append(client_socket)

            for client_socket in disconnected_clients:
                self.remove_client(client_socket)

    @staticmethod
    def _send_message(client_socket: socket.socket, message: dict):
        try:
            json_data = json.dumps(message).encode()
            message_length = len(json_data)
            client_socket.send(message_length.to_bytes(4, 'big'))
            client_socket.send(json_data)
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {e}")

    @staticmethod
    def _receive_message(client_socket: socket.socket) -> dict:
        try:
            client_socket.settimeout(300.0)
            message_length_bytes = client_socket.recv(4)
            if not message_length_bytes:
                raise ConnectionError("Client disconnected")

            message_length = int.from_bytes(message_length_bytes, 'big')
            if message_length > 1024 * 1024:
                raise ValueError("Message too large")

            client_data = b''
            while len(client_data) < message_length:
                remaining_bytes = message_length - len(client_data)
                chunk = client_socket.recv(min(remaining_bytes, 1024))
                if not chunk:
                    raise ConnectionError("Connection broken")
                client_data += chunk

            return json.loads(client_data.decode())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid message format: {e}")
        finally:
            client_socket.settimeout(None)

    def remove_client(self, client_socket: socket.socket):
        with self.clients_lock:
            if client_socket in self.clients:
                username = self.clients[client_socket]
                del self.clients[client_socket]
                try:
                    client_socket.close()
                except:
                    pass
                print(f"Client {username} disconnected")
                leave_message = {
                    "type": "system",
                    "message": f"{username} has left the chat",
                    "timestamp": datetime.now().isoformat()
                }
                self.broadcast(leave_message)
                self.save_message(leave_message)
                self.message_history.append(leave_message)

    def handle_client(self, client_socket: socket.socket, client_address):
        try:
            initial_message = self._receive_message(client_socket)
            username = initial_message.get("username")

            if not username:
                raise ValueError("No username provided")

            with self.clients_lock:
                if username in self.clients.values():
                    self._send_message(client_socket, {
                        "type": "system",
                        "message": "Username already taken"
                    })
                    client_socket.close()
                    return
                self.clients[client_socket] = username

            filtered_history = [
                msg for msg in self.message_history
                if (not msg.get('type') == 'direct' or
                    msg.get('target_user') == username or
                    msg.get('username') == username) and
                   (not msg.get('type') == 'excluded' or
                    msg.get('excluded_user') != username)
            ]
            for message in filtered_history:
                self._send_message(client_socket, message)

            join_message = {
                "type": "system",
                "message": f"{username} has joined the chat",
                "timestamp": datetime.now().isoformat()
            }
            self.broadcast(join_message)
            self.save_message(join_message)
            self.message_history.append(join_message)

            while self.running:
                try:
                    message_data = self._receive_message(client_socket)
                    message_data["username"] = username

                    if message_data.get('message', '').startswith('/'):
                        processed_data = self.handle_command(client_socket, message_data)
                        if processed_data is None:
                            continue
                        processed_message, target_user, excluded_user = processed_data
                    else:
                        processed_message, target_user, excluded_user = self.process_message(message_data)

                    if processed_message:
                        self.message_history.append(processed_message)
                        self.save_message(processed_message)

                        if len(self.message_history) > 20:
                            self.message_history.pop(0)

                        print(f"{username}: {processed_message.get('message', '')}")
                        self.broadcast(processed_message, client_socket, target_user, excluded_user)

                except ConnectionError:
                    break
                except Exception as e:
                    print(f"Error handling message from {username}: {e}")
                    break

        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            self.remove_client(client_socket)

    def shutdown(self):
        print("\nShutting down server...")
        self.running = False

        with self.clients_lock:
            for client_socket in list(self.clients.keys()):
                try:
                    self._send_message(client_socket, {
                        "type": "system",
                        "message": "Server is shutting down"
                    })
                    client_socket.close()
                except:
                    pass
            self.clients.clear()

        try:
            self.server_socket.close()
        except:
            pass
        if self.accept_thread:
            self.accept_thread.join()


def main():
    server = ChatServer('127.0.0.1', 8080)

    def signal_handler():
        server.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
        while server.running:
            time.sleep(0.1)
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()