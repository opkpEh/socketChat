import socket
import json
import threading
from typing import Dict, Set


class ChatServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: Dict[socket.socket, str] = {}  # socket -> username mapping
        self.clients_lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        """Start the chat server"""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"New connection from {client_address}")
            # Start a new thread for each client
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, client_address)
            )
            client_thread.start()

    def broadcast(self, message: dict, sender_socket: socket.socket = None):
        """Send a message to all connected clients except the sender"""
        with self.clients_lock:
            for client_socket in self.clients.keys():
                if client_socket != sender_socket:
                    try:
                        self._send_message(client_socket, message)
                    except Exception as e:
                        print(f"Error broadcasting to client: {e}")
                        self.remove_client(client_socket)

    def _send_message(self, client_socket: socket.socket, message: dict):
        """Send a message to a specific client"""
        json_data = json.dumps(message).encode()
        message_length = len(json_data)
        client_socket.send(message_length.to_bytes(4, 'big'))
        client_socket.send(json_data)

    def _receive_message(self, client_socket: socket.socket) -> dict:
        """Receive a message from a client"""
        message_length_bytes = client_socket.recv(4)
        if not message_length_bytes:
            raise ConnectionError("Client disconnected")

        message_length = int.from_bytes(message_length_bytes, 'big')

        # Receive the full message
        client_data = b''
        while len(client_data) < message_length:
            remaining_bytes = message_length - len(client_data)
            chunk = client_socket.recv(min(remaining_bytes, 1024))
            if not chunk:
                raise ConnectionError("Connection broken")
            client_data += chunk

        return json.loads(client_data.decode())

    def remove_client(self, client_socket: socket.socket):
        """Remove a client from the server"""
        with self.clients_lock:
            if client_socket in self.clients:
                username = self.clients[client_socket]
                del self.clients[client_socket]
                try:
                    client_socket.close()
                except:
                    pass
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
                self.clients[client_socket] = username

            self.broadcast({
                "type": "system",
                "message": f"{username} has joined the chat"
            })

            while True:
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


def main():
    server = ChatServer('10.20.29.33', 8080)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_socket.close()


if __name__ == "__main__":
    main()