import socket
import json
import threading

HOST = '127.0.0.1'
PORT = 8080

def receive_messages(client_socket):
    while True:
        try:
            message_length_bytes = client_socket.recv(4)
            if not message_length_bytes:
                break

            message_length = int.from_bytes(message_length_bytes, 'big')

            #Receive the full message
            client_data = b''
            while len(client_data) < message_length:
                remaining_bytes = message_length- len(client_data)
                chunk = client_socket.recv(min(remaining_bytes, 1024))
                if not chunk:
                    break
                client_data += chunk

            #Parsing and print the message
            data = json.loads(client_data.decode())
            username = data['username']
            message = data['message']
            print(f"\r{username}: {message}")
            print("> ", end='', flush=True)

        except Exception as e:
            print(f"\nError receiving message: {e}")
            break

    client_socket.close()


def send_messages(client_socket, username):
    while True:
        try:
            message = input("> ")

            data = {
                "username": username,
                "message": message
            }

            json_data = json.dumps(data).encode()

            # Send length then message
            message_length = len(json_data)
            client_socket.send(message_length.to_bytes(4, 'big'))
            client_socket.send(json_data)

        except Exception as e:
            print(f"\nError sending message: {e}")
            break

    client_socket.close()


def main():
    global server_username
    server_username = input("Enter server username: ")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"Server listening on {HOST}:{PORT}")

        client_socket, client_address = server_socket.accept()
        print(f"Connected to {client_address}")

        # Create threads for sending and receiving
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        send_thread = threading.Thread(target=send_messages, args=(client_socket, server_username))

        # Start both threads
        receive_thread.start()
        send_thread.start()

        #waiting for both threads to complete
        receive_thread.join()
        send_thread.join()


if __name__ == "__main__":
    main()