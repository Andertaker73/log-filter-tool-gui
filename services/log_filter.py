import re

from pathlib import Path


def sanitize_filename(url):
    sanitized = re.sub(r'[\\/*?:"<>|\r\n]', '_', url)
    sanitized = sanitized.strip('_')
    return sanitized[:251]

def filter_urls(input_file, output_dir, concat_params_list):
    url_files = {}
    output_file_paths = []
    input_file_path = Path(input_file)
    output_dir_path = Path(output_dir)

    if not output_dir_path.exists():
        output_dir_path.mkdir(parents=True, exist_ok=True)

    try:
        with input_file_path.open('r', encoding='utf-8') as log_origin:
            current_url = None
            capture_lines = False

            for line in log_origin:
                match = re.search(r'(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD|TRACE|CONNECT) (.*?) HTTP/1.1', line)
                if match:
                    url = match.group(2)
                    capture_lines = '*ERROR*' in line or 'Error' in line

                    # Ignorar URLs que estão na lista de concatenação
                    if any(concat_param in url for concat_param in concat_params_list):
                        current_url = None  # Ignorar esta URL
                        continue

                    sanitized_url = sanitize_filename(url)
                    output_file = output_dir_path.joinpath(f"{sanitized_url}.log")

                    if url not in url_files:
                        try:
                            url_files[url] = output_file.open('w', encoding='utf-8')
                            output_file_paths.append(output_file)
                            print(f"Criando arquivo filtrado: {output_file}")
                        except Exception as e:
                            print(f"Falha ao criar o arquivo {output_file}: {e}")
                            continue

                    current_url = url
                    url_files[url].write(line)
                elif capture_lines or line.lstrip().startswith("at "):
                    # Anexar a linha subsequente se *ERROR* for encontrado ou se a linha começar com "at"
                    timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                    if not timestamp_match:
                        if current_url:
                            url_files[current_url].write(line)
                    else:
                        capture_lines = False

        for file in url_files.values():
            file.close()

        print(f"Filtrado e criado {len(output_file_paths)} arquivos específicos de URL.")
        return output_file_paths
    except Exception as e:
        print(f"Ocorreu um erro ao filtrar URLs: {e}")
        raise

