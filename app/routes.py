import os
import re
import tempfile
import shutil

from flask import request
from services.checksum import generate_checksum, create_and_save_zip
from services.log_audit import audit_processed_content
from services.log_concat import concat_requests
from services.log_filter import sanitize_filename, filter_urls


def configure_routes(app):
    @app.route('/filter-log', methods=['POST'])
    def filter_log_endpoint():
        try:
            if 'log_file' not in request.files:
                return "Nenhuma parte de arquivo na solicitação", 400

            input_file = request.files['log_file']

            if input_file.filename == '':
                return "Nenhum arquivo selecionado", 400

            output_dir = os.path.join(tempfile.gettempdir(), 'log_filter_output')
            os.makedirs(output_dir, exist_ok=True)

            input_file_path = os.path.join(output_dir, input_file.filename)
            input_file.save(input_file_path)
            print(f"Arquivo salvo em {input_file_path}")

            filter_param = request.form.get('filter_param')
            concat_params = request.form.get('concat_params')

            save_dir = request.form.get('save_dir', output_dir)
            os.makedirs(save_dir, exist_ok=True)

            concat_params_list = []

            if filter_param:
                sanitized_filter_param = sanitize_filename(filter_param.rstrip("/"))
                filtered_file = os.path.join(save_dir, f"filtered_{sanitized_filter_param}.log")

                with open(input_file_path, 'r', encoding='utf-8') as log_origin, open(filtered_file, 'w',
                                                                                      encoding='utf-8') as out_file:
                    capture_lines = False
                    for line in log_origin:
                        if filter_param in line:
                            out_file.write(line)
                            capture_lines = '*ERROR*' in line
                        elif capture_lines:
                            timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                            if not timestamp_match:
                                out_file.write(line)
                            else:
                                capture_lines = False

                return f"Processamento concluído. O arquivo de log está disponível em {filtered_file}", 200

            concat_files = []
            if concat_params:
                concat_params_list = [param.strip() for param in concat_params.split(',')]
                for concat_param in concat_params_list:
                    concat_file = concat_requests(input_file_path, output_dir, concat_param)
                    concat_files.append(concat_file)

            all_output_files = filter_urls(input_file_path, output_dir, concat_params_list)

            if not all_output_files and not concat_files:
                return "Nenhum arquivo filtrado foi criado", 500

            # Realiza auditoria de linhas processadas
            missing_lines_file, extra_lines = audit_processed_content(input_file_path, all_output_files + concat_files,
                                                                      output_dir)

            # Adiciona o arquivo de linhas faltantes (aem_processes.log) aos arquivos processados
            all_output_files.append(missing_lines_file)

            # Gera o checksum
            checksum_log = generate_checksum(input_file_path, all_output_files + concat_files, output_dir)
            all_output_files.append(checksum_log)

            zip_filename = f"filtered_{os.path.splitext(input_file.filename)[0]}.zip"
            zip_filepath = create_and_save_zip(all_output_files, concat_files, zip_filename, output_dir)

            # Verifique se o caminho do arquivo ZIP não é vazio
            if not zip_filepath:
                return "Falha ao criar o arquivo ZIP", 500

            final_zip_path = os.path.join(save_dir, zip_filename)

            shutil.move(zip_filepath, final_zip_path)
            print(f"Arquivo ZIP movido para {final_zip_path}")

            return (f"Processamento concluído. O arquivo ZIP está disponível em {final_zip_path}\n"
                    f"Relatório de Auditoria:\n"
                    f"Linhas faltantes registradas em: {missing_lines_file}\n"
                    f"Linhas processadas que não estavam no original (possível duplicação ou erro): {extra_lines}"), 200

        except Exception as e:
            return f"Ocorreu um erro: {e}", 500
