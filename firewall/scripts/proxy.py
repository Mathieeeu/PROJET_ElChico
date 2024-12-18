# /scripts/proxy.py 

import socket
import threading
import csv
import MySQLdb

def handle_client_request(client_socket, addr):
    try:
        # Recevoir la requête du client
        print("[*] Request received from client")

        # Lire les données du client
        request = b''  # Initialisation de la variable request en bytes
        client_socket.settimeout(1.0)  # Définir un timeout pour éviter de bloquer indéfiniment

        while True:
            try:
                # Recevoir les données du client
                data = client_socket.recv(1024)
                if not data:
                    break
                request += data
                print(f"\033[96m[*] Received {len(data)} bytes\033[0m")
                # print(f"{data.decode('utf-8')}")
            except socket.timeout:
                break

        # Extraire l'hôte et le port de la requête
        host, port = extract_host_port_from_request(request)

        # Créer une socket pour se connecter au serveur distant
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as destination_socket:
            # Se connecter au serveur distant
            destination_socket.connect((host, port))
            destination_socket.settimeout(1.0)  # Définir un timeout pour la réception des données (car on attend toujours ce délai à la fin de la .recv())

            # Envoyer la requête au serveur distant
            destination_socket.sendall(request)

            # Recevoir la réponse du serveur distant
            print("[*] Response received from server")
            response = b''
            CHUNK_SIZE = 1024
            IS_ALLOWED = True
            while True:
                try:
                    data = destination_socket.recv(CHUNK_SIZE)

                    if not data:
                        break

                    print(f"\033[96m[*] Received {len(data)} bytes\033[0m")
                    # print(f"{data.decode('utf-8')}")  # Afficher les données reçues

                    if isAllowed(data, addr[0]):
                        # Ajouter les données à la réponse
                        response += data
                    else:
                        body = b"<h1>403 Forbidden</h1>\r\n"
                        response = b"HTTP/1.1 403 Forbidden\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body + b"\r\n"
                        print("\033[91m[*] Blocked content detected - sending response to client\033[0m")
                        IS_ALLOWED = False
                        break

                except socket.timeout:
                    break                
            # Envoyer la réponse au client
            client_socket.sendall(response)
            add_to_database(addr[0], host, IS_ALLOWED)

    except Exception as e:
        print(f"\033[91m[*][*] Exception: {e}\033[0m")

    finally:
        # Fermer le socket du client
        client_socket.close()
        print(f"[*] Closing connection\n\n")

def extract_host_port_from_request(request):
    # Récupérer la valeur après l'entête "Host:"
    host_string_start = request.find(b"Host: ") + len(b"Host: ")
    host_string_end = request.find(b"\r\n", host_string_start)
    host_string = request[host_string_start:host_string_end].decode("utf-8")

    # Trouver la position du port
    webserver_pos = host_string.find("/")
    if webserver_pos == -1:  # Pas de port spécifié
        webserver_pos = len(host_string)
    port_pos = host_string.find(":")  # Position du port

    if port_pos == -1 or webserver_pos < port_pos:
        # Port par défaut
        port = 80
        host = host_string[:webserver_pos]
    else:
        # Extraire le port spécifié dans l'en-tête "Host:"
        port = int((host_string[(port_pos+1):])[:webserver_pos-port_pos-1])
        host = host_string[:port_pos]

    return host, port

def isAllowed(data,address):
    # Vérifier si le contenu est autorisé
    BAN_WORDS = []
    BYPASS_IPS = []

    with open("scripts/swear_words.csv", "r") as file:
        reader = csv.reader(file)
        for row in reader:
            BAN_WORDS.append(row[0])
        
    with open("scripts/allowed_ips.txt", "r") as file:
        for line in file:
            BYPASS_IPS.append(line.strip())

    if address in BYPASS_IPS: 
        print(f"\033[94m[*] Bypassing firewall for IP: {address}\033[0m")
        return True
    
    # Vérifier toutes les formes d'un mot interdit (avec espaces avant et après, avec point après, pluriel, etc.)
    for word in BAN_WORDS:
        if (" " + word + " ") in data.decode("utf-8").lower():
            print(f"\033[93m[*] Blocked content: word:{word} <---------\033[0m")
            # print(f"\033[93m[*] Blocked content: word:{word} in : {data}\033[0m")
            return False
        if (" " + word + ".") in data.decode("utf-8").lower():
            print(f"\033[93m[*] Blocked content: word:{word} <---------\033[0m")
            # print(f"\033[93m[*] Blocked content: word:{word} in : {data}\033[0m")
            return False
        if (" " + word + "s ") in data.decode("utf-8").lower():
            print(f"\033[93m[*] Blocked content: word:{word} <---------\033[0m")
            # print(f"\033[93m[*] Blocked content: word:{word} in : {data}\033[0m")
            return False
        if (" " + word + "es ") in data.decode("utf-8").lower():
            print(f"\033[93m[*] Blocked content: word:{word} <---------\033[0m")
            # print(f"\033[93m[*] Blocked content: word:{word} in : {data}\033[0m")
            return False
        if (" " + word + "s.") in data.decode("utf-8").lower():
            print(f"\033[93m[*] Blocked content: word:{word} <---------\033[0m")
            # print(f"\033[93m[*] Blocked content: word:{word} in : {data}\033[0m")
            return False
        if (" " + word + "es.") in data.decode("utf-8").lower():
            print(f"\033[93m[*] Blocked content: word:{word} <---------\033[0m")
            # print(f"\033[93m[*] Blocked content: word:{word} in : {data}\033[0m")
            return False
    print("\033[92m[*] Legal content detected - sending response to client\033[0m")
    return True

def add_to_database(source_ip, host, allowed):
    # Ajouter la requete à la base de données
    try:
        # Connexion à la base de données
        connection = MySQLdb.connect(
            host='5.6.1.2',
            user='root',
            passwd='password',
            db='firewall_logs'
        )

        cursor = connection.cursor()
        cursor.execute("USE firewall_logs")
        cursor.execute("INSERT INTO http_requests (source_ip, host, allowed) VALUES (%s, %s, %s)", (source_ip, host, allowed))
        connection.commit()
        print("\033[92m[*] Request added to database\033[0m")

    except MySQLdb.Error as e:
        print("Error while connecting to MySQL", e)

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

# Configuration du proxy
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8888

# Configuration du serveur
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Accepter jusqu'à 5 connexions entrantes
server.bind((PROXY_HOST, PROXY_PORT))
server.listen(5)
print(f"[*] Proxy listening on {PROXY_HOST}:{PROXY_PORT}")

while True:
    # Recevoir la requête du client
    client_socket, addr = server.accept()
    print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")

    # Créer un thread pour gérer la connexion
    client_handler = threading.Thread(target=handle_client_request, args=(client_socket, addr))

    # Démarrer le thread
    client_handler.start()

# Pour tester le proxy, vous pouvez utiliser curl avec un proxy spécifié:
# curl --proxy <adresse_firewall>:8888 httpbin.org/ip   (on spécifie le proxy, on peut aussi mettre -x à la place de --proxy)
# curl httpbin.org/ip     (devrait marcher aussi)

