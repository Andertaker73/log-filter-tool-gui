import os
import tempfile
import re
import time
from flask import Flask, request, send_file
from zipfile import ZipFile
import shutil
from threading import Thread
from werkzeug.serving import WSGIRequestHandler

app = Flask(__name__)

WSGIRequestHandler.protocol_version = "HTTP/1.1"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def sanitize_filename(url):
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', url)
    sanitized = sanitized.strip('_')
    return sanitized[:255]

def filter_urls(input_file, output_dir, concat_params_list):
    url_files = {}
    output_file_paths = []
    capture_lines = False
    try:
        with open(input_file, 'r', encoding='utf-8') as log_origin:
            for line in log_origin:
                match = re.search(r'(GET|POST) (.*?) HTTP/1.1', line)
                if match:
                    url = match.group(2)
                    if any(url.startswith(concat_param) for concat_param in concat_params_list):
                        continue  # Ignore URLs that are in the concat_params_list

                    sanitized_url = sanitize_filename(url)
                    output_file = os.path.join(output_dir, f"{sanitized_url}.log")

                    if url not in url_files:
                        try:
                            url_files[url] = open(output_file, 'w', encoding='utf-8')
                            output_file_paths.append(output_file)
                            print(f"Creating filtered file: {output_file}")
                        except Exception as e:
                            print(f"Failed to create file {output_file}: {e}")
                            continue

                    url_files[url].write(line)
                    capture_lines = '*ERROR*' in line  # Start capturing lines if *ERROR* is found

                elif capture_lines:
                    # Check if the line starts with a timestamp
                    timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                    if not timestamp_match:
                        # If the line doesn't start with a timestamp, append it to the last URL's log file
                        url_files[url].write(line)
                    else:
                        # If a new timestamp is found, stop capturing
                        capture_lines = False

        for file in url_files.values():
            file.close()

        print(f"Filtered and created {len(output_file_paths)} URL-specific files.")
        return output_file_paths
    except Exception as e:
        raise Exception(f"An error occurred while filtering URLs: {e}")

def concat_requests(input_file, output_dir, concat_param):
    sanitized_base_name = sanitize_filename(concat_param.rstrip("/"))
    output_file = os.path.join(output_dir, f"{sanitized_base_name}.log")

    with open(input_file, 'r', encoding='utf-8') as log_origin, open(output_file, 'w', encoding='utf-8') as concat_file:
        lines_to_keep = []
        capture_lines = False
        for line in log_origin:
            if concat_param in line:
                concat_file.write(line)
                capture_lines = '*ERROR*' in line  # Start capturing lines if *ERROR* is found
            elif capture_lines:
                timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                if not timestamp_match:
                    concat_file.write(line)
                else:
                    capture_lines = False
            else:
                lines_to_keep.append(line)

    with open(input_file, 'w', encoding='utf-8') as log_origin:
        log_origin.writelines(lines_to_keep)

    return output_file

def cleanup_files(output_dir, all_output_files, zip_filepath):
    time.sleep(2)
    try:
        for file in all_output_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted temporary file: {file}")
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
            print(f"Deleted ZIP file: {zip_filepath}")
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            print(f"Deleted temporary directory: {output_dir}")
    except Exception as e:
        print(f"Cleanup failed: {e}")

def create_and_save_zip(output_dir, all_output_files, concat_files, zip_filename, save_dir):
    try:
        added_files = set()
        zip_filepath = os.path.join(save_dir, zip_filename)

        with ZipFile(zip_filepath, 'w') as zipf:
            for file in all_output_files:
                if os.path.exists(file) and file not in added_files:
                    zipf.write(file, os.path.basename(file))
                    added_files.add(file)
                    print(f"Added to zip: {file}")
                else:
                    print(f"File already added or does not exist: {file}")

            for concat_file in concat_files:
                if os.path.exists(concat_file) and concat_file not in added_files:
                    zipf.write(concat_file, os.path.basename(concat_file))
                    added_files.add(concat_file)
                    print(f"Added concatenated file to zip: {concat_file}")
                else:
                    print(f"Concatenated file already added or does not exist: {concat_file}")

        print(f"ZIP file saved at {zip_filepath}")
        return zip_filepath  # Retorna o caminho para o arquivo ZIP salvo
    except Exception as e:
        print(f"An error occurred during ZIP creation: {e}")
        return None

@app.route('/filter-log', methods=['POST'])
def filter_log_endpoint():
    try:
        if 'log_file' not in request.files:
            return "No file part in the request", 400

        input_file = request.files['log_file']

        if input_file.filename == '':
            return "No selected file", 400

        output_dir = os.path.join(tempfile.gettempdir(), 'log_filter_output')
        os.makedirs(output_dir, exist_ok=True)

        input_file_path = os.path.join(output_dir, input_file.filename)
        input_file.save(input_file_path)
        print(f"File saved at {input_file_path}")

        filter_param = request.form.get('filter_param')
        concat_params = request.form.get('concat_params')

        # Diretório de salvamento fornecido pelo usuário (ou um diretório padrão)
        save_dir = request.form.get('save_dir', output_dir)
        os.makedirs(save_dir, exist_ok=True)  # Criar o diretório de salvamento, se não existir

        concat_files = []
        if concat_params:
            concat_params_list = [param.strip() for param in concat_params.split(',')]
            for concat_param in concat_params_list:
                concat_file = concat_requests(input_file_path, output_dir, concat_param)
                concat_files.append(concat_file)

        all_output_files = filter_urls(input_file_path, output_dir, concat_params_list if concat_params else [])

        if not all_output_files and not concat_files:
            return "No filtered files were created", 500

        zip_filename = 'filtered_logs.zip'

        # Criar o ZIP no diretório temporário
        zip_filepath = create_and_save_zip(output_dir, all_output_files, concat_files, zip_filename, output_dir)
        if not zip_filepath:
            return "Failed to create ZIP file", 500

        # Mover o ZIP para o diretório especificado
        final_zip_path = os.path.join(save_dir, zip_filename)
        shutil.move(zip_filepath, final_zip_path)
        print(f"ZIP file moved to {final_zip_path}")

        # Limpar arquivos temporários
        cleanup_files(output_dir, all_output_files, zip_filepath)

        return f"Processing completed. The ZIP file is available at {final_zip_path}", 200

    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
