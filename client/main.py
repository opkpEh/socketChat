import socket
import json
import threading

HOST = '127.0.0.1'
PORT = 8080


def receive_message(client_socket):
    try:
        response_length = int.from_bytes(client_socket.recv(4), 'big')

        server_response = b''
        while len(server_response) < response_length:
            remaining_bytes = response_length - len(server_response)
            chunk = client_socket.recv(min(remaining_bytes, 1024))
            if not chunk:
                raise ConnectionError("Server disconnected")
            server_response += chunk

        response_data = json.loads(server_response.decode())
        server_username = response_data['username']
        server_message = response_data['message']

        print(f"\r{server_username}: {server_message}")
        print(f"{client_username}: ", end='', flush=True)

        return True

    except ConnectionError as e:
        print(f"\nConnection error: {e}")
        return False

    except Exception as e:
        print(f"\nError receiving message: {e}")
        return False


def receive_messages(client_socket):
    while True:
        if not receive_message(client_socket):
            break
    client_socket.close()


def send_message(client_socket, message):
    try:
        data = {
            "username": client_username,
            "message": message
        }

        json_data = json.dumps(data).encode()

        message_length = len(json_data)
        client_socket.send(message_length.to_bytes(4, 'big'))
        client_socket.send(json_data)

        return True

    except Exception as e:
        print(f"\nError sending message: {e}")
        return False


def send_messages(client_socket):
    while True:
        try:
            message = input(f"{client_username}: ")
            if not send_message(client_socket, message):
                break

        except KeyboardInterrupt:
            print("\nShutting down...")
            break

    client_socket.close()


def main():
    global client_username

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        print(f'Connected to {HOST}:{PORT}')

        client_username = input("Enter your username: ")

        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        send_thread = threading.Thread(target=send_messages, args=(client_socket,))

        receive_thread.daemon = True  # This closes the thread when main program exits
        send_thread.daemon = True

        receive_thread.start()
        send_thread.start()

        send_thread.join()

    except ConnectionRefusedError:
        print("Could not connect to server. Is it running?")
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass

if __name__ == "__main__":
    main()