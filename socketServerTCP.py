import sqlite3
import socket
import time
import random
import threading

HOST = '0.0.0.0'
ports = [random.randint(1024, 4915) for _ in range(4)]  # Lista de portas aleatórias entre 1024 e 4915
PORT = random.choice(ports)  # Seleciona uma porta aleatória da lista
print(f"Servidor iniciado em {HOST}:{PORT}")

# Conecta ao banco de dados SQLite
conn_db = sqlite3.connect('clientes.db', check_same_thread=False)  # check permite várias conexões no banco em threads diferentes
cursor = conn_db.cursor()

# Cria a tabela 'clientes' se ela não existir
cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (id TEXT, endereco TEXT, timestamp TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens (dst TEXT, src TEXT, timestamp TEXT, msg_data TEXT)''')
conn_db.commit()

# Dicionário global para armazenar as conexões dos clientes
client_connections = {}
client_connections_lock = threading.Lock()  # Lock para sincronizar o acesso ao dicionário

def handle_client(conn, addr):
    print(f"Conectado por {addr}")

    # Envia uma mensagem inicial para o cliente
    conn.sendall("Bem-vindo ao servidor. Envie '01' para se cadastrar. \n".encode())

    # Recebe dados do cliente
    data = conn.recv(1024).decode()
    print(f"Recebido do cliente: {data} \n")

    unique_id = None
    if data == '01':
        # Verifica se já existe um ID associado a este IP
        cursor.execute("SELECT id FROM clientes WHERE endereco=?", (addr[0],))
        existing_id = cursor.fetchone()

        if existing_id:
            unique_id = existing_id[0]
            print(f"Conectado por {addr} com ID {unique_id} \n")
            conn.sendall(f"02{unique_id} \n".encode())
        else:
            # Se não existe ID, cria um novo ID
            unique_id = ''.join([str(random.randint(0, 9)) for _ in range(13)])
            conn.sendall(f"02{unique_id} \n".encode())

            # Insere o ID único e o endereço do cliente no banco de dados
            cursor.execute("INSERT INTO clientes (id, endereco, timestamp) VALUES (?, ?, ?)",
                           (unique_id, addr[0], str(int(time.time()))))
            conn_db.commit()
    else:
        conn.sendall("Mensagem inválida. Envie '01' para se cadastrar. \n".encode())

    # Adicionar a conexão do cliente ao dicionário global
    if unique_id:
        with client_connections_lock:
            client_connections[unique_id] = conn
        print(f"Usuários conectados: {list(client_connections.keys())} \n")

        # Verificar se há mensagens pendentes para o cliente
        cursor.execute("SELECT src, timestamp, msg_data FROM mensagens WHERE dst=?", (unique_id,))
        pending_messages = cursor.fetchall()
        for msg in pending_messages:
            src, timestamp, msg_data = msg
            conn.sendall(f"{src}{unique_id}{timestamp}{msg_data}".encode())

        # Remover as mensagens pendentes entregues
        cursor.execute("DELETE FROM mensagens WHERE dst=?", (unique_id,))
        conn_db.commit()

    try:
        # Recebe dados do cliente
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                message = data.decode()
                print(f"Recebido de {unique_id}: {message} \n")

                if len(message) >= 256:
                    conn.sendall(f"Erro: Mensagem deve ter no máximo 256 caracteres! \n".encode())
                else:
                    cod = message[:2]
                    src = message[2:15].strip()  # Remove espaços extras
                    dst = message[15:30].strip()  # Remove espaços extras
                    timestamp = message[30:40]
                    msg_data = message[40:]

                    print(f"Mensagem decodificada - COD: {cod}, SRC: {src}, DST: '{dst}', TIMESTAMP: {timestamp}, DATA: {msg_data}")

                    with client_connections_lock:
                        if dst in client_connections:
                            dest_conn = client_connections[dst]
                            dest_conn.sendall(data)
                            conn.sendall(f"Sucesso: Mensagem enviada para {dst}! \n".encode())
                        else:
                            # Armazena a mensagem no banco de dados se o destinatário não estiver online
                            cursor.execute("INSERT INTO mensagens (dst, src, timestamp, msg_data) VALUES (?, ?, ?, ?)",
                                           (dst, src, timestamp, msg_data))
                            conn_db.commit()
                            conn.sendall(f"Erro: Destino {dst} não encontrado. Mensagem armazenada para entrega futura. \n".encode())
            except ConnectionResetError:
                print(f"Conexão resetada pelo cliente {addr}.")
                break
    finally:
        # Remove a conexão do cliente do dicionário global
        if unique_id:
            with client_connections_lock:
                if unique_id in client_connections:
                    del client_connections[unique_id]

        print(f"Conexão encerrada com {addr}.")
        conn.close()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Aguardando conexões na porta {PORT}...")
    while True:
        conn, addr = s.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()