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
                    print(f"Creating new part file: {part_file_path}")
                    part_files.append(part_file_path)
                    current_part = open(part_file_path, 'w', encoding='utf-8')
                    current_size = 0

                if current_part is None:
                    part_number += 1
                    part_file_path = os.path.join(output_dir, f"log_part_{part_number}.log")
                    print(f"Creating initial part file: {part_file_path}")
                    part_files.append(part_file_path)
                    current_part = open(part_file_path, 'w', encoding='utf-8')

                current_part.write(line)
                current_size += len(line.encode('utf-8'))

            if current_part:
                current_part.close()

        print(f"Created {len(part_files)} part files.")
        return part_files
    except Exception as e:
        raise Exception(f"An error occurred while splitting the log file: {e}")

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

def cleanup_files(output_dir, all_output_files, log_parts, zip_filepath):
    time.sleep(2)
    try:
        for file in all_output_files + log_parts:
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

        log_parts = split_log_file(input_file_path, output_dir)

        if not log_parts:
            return "No log parts were created", 500

        if concat_params:
            concat_files = []
            concat_params_list = [param.strip() for param in concat_params.split(',')]
            for log_part in log_parts:
                for concat_param in concat_params_list:
                    concat_file = concat_requests(log_part, output_dir, concat_param)
                    concat_files.append(concat_file)
            if concat_files:
                final_concat_file = concat_files[0]

        all_output_files = []
        for log_part in log_parts:
            output_files = filter_urls(log_part, output_dir, concat_params_list if concat_params else [])
            all_output_files.extend(output_files)

        if not all_output_files and not concat_files:
            return "No filtered files were created", 500

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

            if concat_params:
                for concat_file in concat_files:
                    if os.path.exists(concat_file) and concat_file not in added_files:
                        zipf.write(concat_file, os.path.basename(concat_file))
                        added_files.add(concat_file)
                        print(f"Added concatenated file to zip: {concat_file}")  # Debugging line
                    else:
                        print(f"Concatenated file already added or does not exist: {concat_file}")  # Debugging line

        print(f"ZIP file created at {zip_filepath}")

        return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)

    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
