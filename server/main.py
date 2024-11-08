import socket
import json
import threading
import signal
import time
from typing import Dict

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

    def broadcast(self, message: dict, sender_socket: socket.socket = None):
        with self.clients_lock:
            disconnected_clients = []
            for client_socket in self.clients.keys():
                if client_socket != sender_socket:
                    try:
                        self._send_message(client_socket, message)
                    except Exception as e:
                        print(f"Error broadcasting to client {self.clients.get(client_socket, 'unknown')}: {e}")
                        disconnected_clients.append(client_socket)

            for client_socket in disconnected_clients:
                self.remove_client(client_socket)

    def _send_message(self, client_socket: socket.socket, message: dict):
        try:
            json_data = json.dumps(message).encode()
            message_length = len(json_data)
            client_socket.send(message_length.to_bytes(4, 'big'))
            client_socket.send(json_data)
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {e}")

    def _receive_message(self, client_socket: socket.socket) -> dict:
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
                self.broadcast({
                    "type": "system",
                    "message": f"{username} has left the chat"
                })

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

            self.broadcast({
                "type": "system",
                "message": f"{username} has joined the chat"
            })

            while self.running:
                try:
                    message_data = self._receive_message(client_socket)
                    message_data["username"] = username
                    print(f"{username}: {message_data.get('message', '')}")
                    self.broadcast(message_data, client_socket)
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

    def signal_handler(signum, frame):
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