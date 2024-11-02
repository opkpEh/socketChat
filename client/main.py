import socket

HOST = '127.0.0.1'
PORT = 8080

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))
    print(f'Connected to {HOST}:{PORT}')

    while True:
        try:
            message = input("Your message: ")
            client_socket.send(message.encode())

            server_reponse = client_socket.recv(1024).decode()
            print(f'Server: {server_reponse}')

        except KeyboardInterrupt:
            print('Shutting down...')
            client_socket.close()
            break