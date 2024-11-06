import socket
import json
import threading
import sys
import time


class ChatClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.connected = False
        self.receive_thread = None
        self.send_thread = None

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

            if message.get('type') == 'system':
                print(f"\r\033[K[System] {message['message']}")
            else:
                sender = message.get('username', 'Unknown')
                content = message.get('message', '')
                print(f"\r\033[K{sender}: {content}")

            print("> ", end='', flush=True)
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

    def send_message(self, message: str) -> bool:
        try:
            if message.lower() == '/quit':
                self.connected = False
                return False

            data = {
                "type": "message",
                "username": self.username,
                "message": message
            }
            json_data = json.dumps(data).encode()

            message_length = len(json_data)
            self.socket.send(message_length.to_bytes(4, 'big'))
            self.socket.send(json_data)
            return True

        except Exception as e:
            print(f"\nError sending message: {e}")
            self.connected = False
            return False

    def receive_loop(self):
        while self.connected:
            if not self.receive_message():
                break
        self.cleanup()

    def send_loop(self):
        while self.connected:
            try:
                message = input("> ")
                if not self.send_message(message):
                    break
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

        self.username = input("Enter your username: ")

        join_message = {
            "type": "join",
            "username": self.username,
            "message": "joined the chat"
        }
        json_data = json.dumps(join_message).encode()
        self.socket.send(len(json_data).to_bytes(4, 'big'))
        self.socket.send(json_data)

        self.receive_thread = threading.Thread(target=self.receive_loop)
        self.send_thread = threading.Thread(target=self.send_loop)

        self.receive_thread.daemon = True
        self.send_thread.daemon = True

        self.receive_thread.start()
        self.send_thread.start()

        try:
            self.send_thread.join()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.cleanup()


def main():
    client = ChatClient('10.20.29.33', 8080)
    client.start()


if __name__ == "__main__":
    main()