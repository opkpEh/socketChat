import socket

HOST = '127.0.0.1'
PORT = 8080

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server listening on {HOST}:{PORT}")

    client_socket, client_address = server_socket.accept()

    with client_socket:
        print(f"Connected to {client_address}")
        while True:
            try:
                client_message = client_socket.recv(1024).decode()
                if not client_message:
                    break
                print(f"Client: {client_message}")

                server_message = input("You: ")
                client_socket.sendall(server_message.encode())

            except KeyboardInterrupt:
                print("\nServer shutting down...")
                break