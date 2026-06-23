#ye
import socket

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:

    port = 9001
    server_socket.bind(('0.0.0.0', port))
    
    subscribers = set()
    current_text = ""
    sequence = 0

    while True:

        dgram, address = server_socket.recvfrom(1024)
        message = dgram.decode("utf-8")
        command, separator, argument = message.partition(" ") # split into command and arg

        if command not in ("JOIN", "UPDATE", "LEAVE"):
            print("invalid command")

        elif command == "JOIN" and not argument:
            subscribers.add(address)
            response = f"TEXT {sequence} {current_text}"
            server_socket.sendto(response.encode("utf-8"), address)

        elif command == "LEAVE" and not argument:
            server_socket.sendto(("goodbye").encode("utf-8"), address)
            subscribers.discard(address)

        elif command == "UPDATE":
            if address not in subscribers:
                print("ignored update from unsubscribed client")
            else:
                current_text = argument
                sequence += 1
                response = f"TEXT {sequence} {argument}"

                for subscriber_address in subscribers: 
                    server_socket.sendto((response.encode("utf-8")), subscriber_address)
        else:
            print("invalid request")
