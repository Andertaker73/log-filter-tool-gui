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
    return sanitized[:251]

def filter_urls(input_file, output_dir, concat_params_list):
    url_files = {}
    output_file_paths = []
    try:
        with open(input_file, 'r', encoding='utf-8') as log_origin:
            capture_lines = False
            current_url = None

            for line in log_origin:
                match = re.search(r'(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD|TRACE|CONNECT) (.*?) HTTP/1.1', line)
                if match:
                    url = match.group(2)
                    capture_lines = '*ERROR*' in line

                    if any(url.startswith(concat_param) for concat_param in concat_params_list):
                        current_url = None  # Ignore this URL
                        continue

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

                    current_url = url
                    url_files[url].write(line)
                elif capture_lines and current_url:
                    # Append the subsequent line if *ERROR* is found and the line doesn't start with a timestamp
                    timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                    if not timestamp_match:
                        url_files[current_url].write(line)
                    else:
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
        capture_lines = False
        for line in log_origin:
            if concat_param in line:
                concat_file.write(line)
                capture_lines = '*ERROR*' in line
            elif capture_lines:
                timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                if not timestamp_match:
                    concat_file.write(line)
                else:
                    capture_lines = False

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

def generate_checksum(input_file, all_output_files, output_dir):
    original_line_count = 0
    original_char_count = 0
    processed_line_count = 0
    processed_char_count = 0

    # Contar as linhas e caracteres do arquivo original
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            original_line_count += 1
            original_char_count += len(line)

    # Contar as linhas e caracteres dos arquivos processados
    for processed_file in all_output_files:
        with open(processed_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed_line_count += 1
                processed_char_count += len(line)

    # Criar o relatório de checksum
    checksum_log = os.path.join(output_dir, "checksum.log")
    with open(checksum_log, 'w', encoding='utf-8') as log:
        log.write(f"Linhas arquivo original: {original_line_count}\n")
        log.write(f"Linhas processadas: {processed_line_count}\n")
        log.write(f"Caracteres totais arquivo original: {original_char_count}\n")
        log.write(f"Caracteres totais processados: {processed_char_count}\n")

    print(f"Checksum log created at {checksum_log}")

    return checksum_log

def audit_processed_content(input_file, all_output_files, output_dir):
    input_lines_dict = {}
    processed_lines_dict = {}

    # Contar as ocorrências de cada linha no arquivo original
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            input_lines_dict[line] = input_lines_dict.get(line, 0) + 1

    # Contar as ocorrências de cada linha nos arquivos processados
    for processed_file in all_output_files:
        with open(processed_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed_lines_dict[line] = processed_lines_dict.get(line, 0) + 1

    missing_lines = []
    extra_lines = 0

    # Identificar e registrar as linhas que estão faltando no processamento
    for line, count in input_lines_dict.items():
        if line not in processed_lines_dict or processed_lines_dict[line] < count:
            missing_count = count - processed_lines_dict.get(line, 0)
            for _ in range(missing_count):
                missing_lines.append(line)

    # Registrar as linhas que foram processadas em excesso (possível duplicação ou erro)
    for line, count in processed_lines_dict.items():
        if line not in input_lines_dict:
            extra_lines += count
        elif processed_lines_dict[line] > input_lines_dict[line]:
            extra_lines += (processed_lines_dict[line] - input_lines_dict[line])

    # Criar o relatório detalhado das linhas faltantes
    missing_lines_file = os.path.join(output_dir, "missing_lines.log")
    with open(missing_lines_file, 'w', encoding='utf-8') as log:
        for line in missing_lines:
            log.write(line)

    print(f"Missing lines log created at {missing_lines_file}")

    return missing_lines_file, extra_lines

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

        save_dir = request.form.get('save_dir', output_dir)
        os.makedirs(save_dir, exist_ok=True)

        if filter_param:
            # Gerar um único arquivo filtrado com o nome filtered_{url_sanitizada}.log
            sanitized_filter_param = sanitize_filename(filter_param.rstrip("/"))
            filtered_file = os.path.join(save_dir, f"filtered_{sanitized_filter_param}.log")

            with open(input_file_path, 'r', encoding='utf-8') as log_origin, open(filtered_file, 'w', encoding='utf-8') as out_file:
                capture_lines = False
                for line in log_origin:
                    if filter_param in line:
                        out_file.write(line)
                        capture_lines = '*ERROR*' in line  # Start capturing lines if *ERROR* is found
                    elif capture_lines:
                        timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                        if not timestamp_match:
                            out_file.write(line)
                        else:
                            capture_lines = False

            # Relatar conclusão
            return f"Processing completed. The log file is available at {filtered_file}", 200

        # Caso não haja filter_param, processar normalmente
        concat_files = []
        if concat_params:
            concat_params_list = [param.strip() for param in concat_params.split(',')]
            for concat_param in concat_params_list:
                concat_file = concat_requests(input_file_path, output_dir, concat_param)
                concat_files.append(concat_file)

        all_output_files = filter_urls(input_file_path, output_dir, concat_params_list if concat_params else [])

        if not all_output_files and not concat_files:
            return "No filtered files were created", 500

        # Auditoria do conteúdo processado
        missing_lines_file, extra_lines = audit_processed_content(input_file_path, all_output_files + concat_files, output_dir)

        checksum_log = generate_checksum(input_file_path, all_output_files + concat_files, output_dir)
        all_output_files.extend([checksum_log, missing_lines_file])

        # Criação do arquivo ZIP e relatório final
        zip_filename = f"filtered_{os.path.splitext(input_file.filename)[0]}.zip"
        zip_filepath = create_and_save_zip(output_dir, all_output_files, concat_files, zip_filename, output_dir)
        if not zip_filepath:
            return "Failed to create ZIP file", 500

        final_zip_path = os.path.join(save_dir, zip_filename)
        shutil.move(zip_filepath, final_zip_path)
        print(f"ZIP file moved to {final_zip_path}")

        return (f"Processing completed. The ZIP file is available at {final_zip_path}\n"
                f"Audit Report:\n"
                f"Missing lines are recorded in: {missing_lines_file}\n"
                f"Linhas processadas que não estavam no original (possível duplicação ou erro): {extra_lines}"), 200

    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
