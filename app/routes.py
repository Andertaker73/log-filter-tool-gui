import os
import tempfile
import shutil

from flask import request
from services import log_filter, log_audit, checksum


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

            filter_param = request.form.get('filter_param')
            concat_params = request.form.get('concat_params')
            save_dir = request.form.get('save_dir', output_dir)
            os.makedirs(save_dir, exist_ok=True)

            concat_params_list = []
            if concat_params:
                concat_params_list = [param.strip() for param in concat_params.split(',')]

            all_output_files = log_filter.filter_urls(input_file_path, output_dir, concat_params_list)

            if not all_output_files:
                return "Nenhum arquivo filtrado foi criado", 500

            missing_lines_file, extra_lines = log_audit.audit_processed_content(input_file_path, all_output_files,
                                                                                output_dir)
            all_output_files.append(missing_lines_file)

            checksum_log = checksum.generate_checksum(input_file_path, all_output_files, output_dir)
            all_output_files.append(checksum_log)

            zip_filename = f"filtered_{os.path.splitext(input_file.filename)[0]}.zip"
            zip_filepath = checksum.create_and_save_zip(all_output_files, [], zip_filename, output_dir)

            if not zip_filepath:
                return "Falha ao criar o arquivo ZIP", 500

            final_zip_path = os.path.join(save_dir, zip_filename)
            shutil.move(zip_filepath, final_zip_path)

            return f"Processamento concluído. O arquivo ZIP está disponível em {final_zip_path}", 200

        except Exception as e:
            return f"Ocorreu um erro: {e}", 500
