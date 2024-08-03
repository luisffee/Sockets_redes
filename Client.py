import socket
import time
import datetime

def start_client(server_host='192.168.8.18', server_port=3917):
    # Criar um socket TCP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Definir timeout
    client_socket.settimeout(10.0)  # Timeout de 10 segundos

    try:
        # Conectar ao servidor
        client_socket.connect((server_host, server_port))
        print(f"Conectado ao servidor em {server_host}:{server_port} \n")

        # Receber mensagem inicial do servidor
        initial_message = client_socket.recv(1024).decode()
        print(f"Mensagem do servidor: {initial_message} \n")

        # Enviar '01' para se cadastrar
        message = "01"
        client_socket.sendall(message.encode())
        print("Mensagem '01' enviada. \n")

        # Receber o ID único do servidor
        modified_id = client_socket.recv(1024).decode()
        print(f"Recebido do servidor: {modified_id} \n")
        unique_id = modified_id[2:]
        print(f"ID único: {unique_id} \n")

        def convert_timestamp(timestamp):
            # Converter o timestamp Unix para um objeto datetime
            dt_object = datetime.datetime.fromtimestamp(timestamp)
            
            # Formatar o objeto datetime para uma string legível
            human_readable_time = dt_object.strftime('%H:%M:%S em %d/%m/%Y')
            
            return human_readable_time

        while True:
            print("Menu:")
            print("1. Enviar mensagem")
            print("2. Verificar mensagens recebidas")
            choice = input("Escolha uma opção: ")

            if choice == '1':
                # Enviar mensagem ao servidor
                recipient_id = input("Digite o ID do destinatário (13 dígitos): ")
                if len(recipient_id) != 13:
                    print("O ID do destinatário deve ter exatamente 13 dígitos. \n")
                    continue

                message_content = input("Digite o conteúdo da mensagem (máximo de 218 caracteres): ")
                if len(message_content) > 218:
                    print("O conteúdo da mensagem deve ter no máximo 218 caracteres. \n")
                    continue

                timestamp = int(time.time())
                # Formatar a mensagem com '03', o ID do cliente, ID do destinatário, timestamp e conteúdo da mensagem
                formatted_message = f'03{unique_id}{recipient_id}{timestamp}{message_content.replace(" ", "_")}'
                client_socket.sendall(formatted_message.encode())
                print("Mensagem enviada ao servidor: ", formatted_message + "\n")

            elif choice == '2':
                # Verificar se há mensagens do servidor
                try:
                    data = client_socket.recv(1024).decode()
                    if data:
                        if data.startswith("Sucesso") or data.startswith("Erro"):
                            print(f"Resposta do servidor: {data} \n")
                        else:
                            # Processar mensagem recebida (resposta do servidor com dados de quem enviou e data)
                            src_id = data[2:15].strip()  # ID do remetente
                            timestamp = int(data[30:40])  # Timestamp
                            message_data = data[40:].strip().replace("_", " ")  # Conteúdo da mensagem

                            print(f"Mensagem recebida de {src_id} em {convert_timestamp(timestamp)}: {message_data} \n")
                    else:
                        print("Nenhuma mensagem recebida. \n")
                except socket.timeout:
                    print("Nenhuma mensagem recebida. \n")
            else:
                print("Opção inválida. Por favor, escolha 1 ou 2. \n")

    finally:
        # Fecha o socket independentemente de como o loop while termina
        client_socket.close()

if __name__ == '__main__':
    start_client(server_host='192.168.8.18', server_port=3917)