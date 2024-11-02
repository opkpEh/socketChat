import socket
import json

HOST = '127.0.0.1'
PORT = 8080

server_username = input("Enter a username: ")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server listening on {HOST}:{PORT}")

    client_socket, client_address = server_socket.accept()

    with client_socket:
        print(f"Connected to {client_address}")
        while True:
            try:
                message_length_bytes = client_socket.recv(4)
                if not message_length_bytes:
                    break

                message_length = int.from_bytes(message_length_bytes, 'big')

                client_data = b''
                while len(client_data) < message_length:
                    chunk = client_socket.recv(min(message_length - len(client_data), 1024))
                    if not chunk:
                        break
                    client_data += chunk

                data = json.loads(client_data.decode())
                username = data['username']
                message = data['message']

                print(f"{username}> {message}")

                server_message = input("> ")

                response_data= {
                    "username": server_username,
                    "message": server_message
                }

                response_bytes_json = json.dumps(response_data).encode()

                response_length = len(response_bytes_json)
                client_socket.send(response_length.to_bytes(4, 'big'))

                client_socket.sendall(response_bytes_json)

            except KeyboardInterrupt:
                print("\nServer shutting down...")
                break
            except json.JSONDecodeError:
                print("Error: Received invalid JSON data")
                break
            except Exception as e:
                print(f"Error: {e}")
                break