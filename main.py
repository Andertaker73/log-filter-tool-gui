import os
import tempfile
import re
import time
from flask import Flask, request, send_file
from zipfile import ZipFile
import shutil
from threading import Thread

app = Flask(__name__)

MAX_PART_SIZE = 200 * 1024 * 1024  # 200 MB em bytes

def split_log_file(input_file, output_dir, max_size=MAX_PART_SIZE):
    """
    Divide o arquivo de log em partes menores de até 200MB.
    """
    part_number = 0
    current_size = 0
    part_files = []
    current_part = None

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if current_size + len(line.encode('utf-8')) > max_size:
                    if current_part:
                        current_part.close()
                    part_number += 1
                    part_file_path = os.path.join(output_dir, f"log_part_{part_number}.log")
                    print(f"Creating new part file: {part_file_path}")  # Debugging line
                    part_files.append(part_file_path)
                    current_part = open(part_file_path, 'w', encoding='utf-8')
                    current_size = 0

                if current_part is None:
                    # Garantir que pelo menos uma parte seja criada
                    part_number += 1
                    part_file_path = os.path.join(output_dir, f"log_part_{part_number}.log")
                    print(f"Creating initial part file: {part_file_path}")  # Debugging line
                    part_files.append(part_file_path)
                    current_part = open(part_file_path, 'w', encoding='utf-8')

                current_part.write(line)
                current_size += len(line.encode('utf-8'))

            if current_part:
                current_part.close()

        print(f"Created {len(part_files)} part files.")  # Debugging line
        return part_files
    except Exception as e:
        raise Exception(f"An error occurred while splitting the log file: {e}")

def sanitize_filename(url):
    """
    Sanitiza o nome do arquivo para garantir que seja válido em todos os sistemas de arquivos.
    Substitui caracteres inválidos por underscores.
    """
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', url)
    sanitized = sanitized.strip('_')  # Remove underscores do início/fim
    return sanitized[:255]  # Limite típico de sistemas de arquivos

def filter_urls(input_file, output_dir):
    """
    Filtra as URLs do arquivo de log e cria arquivos separados para cada URL.
    Retorna a lista de caminhos dos arquivos filtrados.
    """
    url_files = {}
    output_file_paths = []
    try:
        with open(input_file, 'r', encoding='utf-8') as log_origin:
            for line in log_origin:
                match = re.search(r'(GET|POST) (.*?) HTTP/1.1', line)
                if match:
                    url = match.group(2)
                    sanitized_url = sanitize_filename(url)
                    output_file = os.path.join(output_dir, f"{sanitized_url}.log")

                    if url not in url_files:
                        try:
                            # Abrir o arquivo de saída
                            url_files[url] = open(output_file, 'w', encoding='utf-8')
                            output_file_paths.append(output_file)
                            print(f"Creating filtered file: {output_file}")  # Debugging line
                        except Exception as e:
                            print(f"Failed to create file {output_file}: {e}")
                            continue

                    url_files[url].write(line)

        for file in url_files.values():
            file.close()

        print(f"Filtered and created {len(output_file_paths)} URL-specific files.")  # Debugging line
        return output_file_paths  # Retorna a lista de caminhos dos arquivos
    except Exception as e:
        raise Exception(f"An error occurred while filtering URLs: {e}")

def cleanup_files(output_dir, all_output_files, log_parts, zip_filepath):
    """
    Limpa arquivos temporários e diretório após o download do zip.
    """
    time.sleep(2)  # Atraso para garantir que o arquivo não esteja mais em uso
    try:
        for file in all_output_files + log_parts:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted temporary file: {file}")  # Debugging line
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
            print(f"Deleted ZIP file: {zip_filepath}")  # Debugging line
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            print(f"Deleted temporary directory: {output_dir}")  # Debugging line
    except Exception as e:
        print(f"Cleanup failed: {e}")

@app.route('/filter-log', methods=['POST'])
def filter_log_endpoint():
    try:
        if 'log_file' not in request.files:
            return "No file part in the request", 400

        input_file = request.files['log_file']

        if input_file.filename == '':
            return "No selected file", 400

        # Gerar um caminho temporário para o arquivo de entrada
        output_dir = os.path.join(tempfile.gettempdir(), 'log_filter_output')
        os.makedirs(output_dir, exist_ok=True)

        input_file_path = os.path.join(output_dir, input_file.filename)
        input_file.save(input_file_path)
        print(f"File saved at {input_file_path}")  # Debugging line

        # Obter o parâmetro opcional
        filter_param = request.form.get('filter_param')

        # Dividir o arquivo de log em partes menores
        log_parts = split_log_file(input_file_path, output_dir)

        if not log_parts:
            return "No log parts were created", 500

        if filter_param:
            # Gerar um único arquivo filtrado
            filtered_file_path = os.path.join(output_dir, f"filtered_{sanitize_filename(filter_param)}.log")
            with open(filtered_file_path, 'w', encoding='utf-8') as filtered_file:
                for log_part in log_parts:
                    with open(log_part, 'r', encoding='utf-8') as part:
                        for line in part:
                            if filter_param in line:
                                filtered_file.write(line)
            print(f"Filtered file created at {filtered_file_path}")  # Debugging line

            # Retornar o arquivo filtrado diretamente
            return send_file(filtered_file_path, as_attachment=True, download_name=os.path.basename(filtered_file_path))

        else:
            # Aplicar o filtro em cada parte do log e criar arquivos separados para cada URL
            all_output_files = []
            for log_part in log_parts:
                output_files = filter_urls(log_part, output_dir)
                all_output_files.extend(output_files)

            if not all_output_files:
                return "No filtered files were created", 500

            # Usar um set para rastrear arquivos já adicionados ao zip
            added_files = set()
            zip_filename = 'filtered_logs.zip'
            zip_filepath = os.path.join(output_dir, zip_filename)
            with ZipFile(zip_filepath, 'w') as zipf:
                for file in all_output_files:
                    if os.path.exists(file) and file not in added_files:
                        zipf.write(file, os.path.basename(file))
                        added_files.add(file)
                        print(f"Added to zip: {file}")  # Debugging line
                    else:
                        print(f"File already added or does not exist: {file}")  # Debugging line

            print(f"ZIP file created at {zip_filepath}")  # Debugging line

            return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)

    except Exception as e:
        return f"An error occurred: {e}", 500


if __name__ == '__main__':
    app.run(debug=True)
