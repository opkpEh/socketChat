import socket
import json

HOST = '127.0.0.1'
PORT = 8080

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))
    print(f'Connected to {HOST}:{PORT}')

    client_username = input("Enter a username: ")

    while True:
        try:
            message = input("> ")

            data = {
                "username": client_username,
                "message": message
            }

            json_data = json.dumps(data).encode()

            message_length = len(json_data)
            client_socket.send(message_length.to_bytes(4, 'big'))

            client_socket.send(json_data)

            response_length = int.from_bytes(client_socket.recv(4), 'big')

            server_response = b''
            while len(server_response) < response_length:

                remaining_bytes= response_length - len(server_response)

                chunk = client_socket.recv(min(remaining_bytes, 1024))
                if not chunk:
                    break
                server_response += chunk

            response_data = json.loads(server_response.decode())
            server_username = response_data['username']
            server_message = response_data['message']

            print(f"{server_username}: {server_message}")

        except KeyboardInterrupt:
            print('\nShutting down...')
            client_socket.close()
            break
        except Exception as e:
            print(f'Error: {e}')
            client_socket.close()
            break