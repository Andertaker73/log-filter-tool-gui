import sys
import re
import tempfile
import shutil
import pythoncom
import os
from win32com.client import Dispatch
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QTextEdit)
from services.checksum import generate_checksum, create_and_save_zip
from services.file_cleanup import cleanup_files
from services.log_audit import audit_processed_content
from services.log_concat import concat_requests
from services.log_filter import sanitize_filename, filter_urls

def create_bat_file_and_shortcut():
    # Caminho do projeto e nome do arquivo .bat
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # Diretório do projeto
    bat_file_path = os.path.join(project_dir, 'run_log_filter_tool.bat')

    # Conteúdo do arquivo .bat
    bat_content = '''@echo off
    cd /d {project_dir}
    call .venv\\Scripts\\activate
    pythonw main.py
    deactivate
    '''.format(project_dir=project_dir)

    # Escreve o arquivo .bat na raiz do projeto
    with open(bat_file_path, 'w') as bat_file:
        bat_file.write(bat_content)

    # Solicita ao usuário o local para salvar o atalho
    shortcut_dir = QFileDialog.getExistingDirectory(None, "Selecionar diretório para salvar o atalho")

    if shortcut_dir:
        # Caminho do atalho
        shortcut_path = os.path.join(shortcut_dir, 'Atalho - LogFilterTool.lnk')

        # Cria o atalho
        pythoncom.CoInitialize()  # Necessário para evitar problemas em alguns sistemas
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)

        # Define o caminho para o arquivo .bat
        shortcut.TargetPath = bat_file_path
        shortcut.WorkingDirectory = project_dir
        shortcut.WindowStyle = 7  # 7: Executar minimizado
        shortcut.save()

        return shortcut_path
    else:
        return None

class LogFilterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.create_shortcut_button = None
        self.log_file_button = None
        self.log_file_label = None
        self.log_file_path = None
        self.filter_param_label = None
        self.filter_param_input = None
        self.concat_params_label = None
        self.concat_params_input = None
        self.save_dir = None
        self.save_dir_label = None
        self.save_dir_button = None
        self.process_button = None
        self.result_text = None
        self.setWindowTitle("Log Filter Tool")
        self.setGeometry(100, 100, 600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Adicionando o label e botão para escolher o diretório do arquivo .bat
        self.create_shortcut_button = QPushButton("Criar atalho")
        self.create_shortcut_button.clicked.connect(create_bat_file_and_shortcut)
        layout.addWidget(self.create_shortcut_button)

        self.log_file_button = QPushButton("Selecionar arquivo de log")
        self.log_file_label = QLabel("Arquivo selecionado")
        self.log_file_button.clicked.connect(self.select_log_file)
        layout.addWidget(self.log_file_button)
        layout.addWidget(self.log_file_label)

        self.filter_param_label = QLabel("Filtrar por parâmetro (gera apenas um log):")
        self.filter_param_input = QLineEdit()
        layout.addWidget(self.filter_param_label)
        layout.addWidget(self.filter_param_input)

        self.concat_params_label = QLabel("Concatenar parâmetros (aceita múltiplos parametros – separar por vírgula):")
        self.concat_params_input = QLineEdit()
        layout.addWidget(self.concat_params_label)
        layout.addWidget(self.concat_params_input)

        self.save_dir_button = QPushButton("Salvar em...")
        self.save_dir_label = QLabel("Diretório:")
        self.save_dir_button.clicked.connect(self.select_save_dir)
        layout.addWidget(self.save_dir_button)
        layout.addWidget(self.save_dir_label)

        self.process_button = QPushButton("Processar log")
        self.process_button.clicked.connect(self.process_log)
        layout.addWidget(self.process_button)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def select_log_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo de log")
        if file_name:
            self.log_file_path = file_name
            self.log_file_label.setText(f"Arquivo selecionado: {file_name}")

    def select_save_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Salvar em...")
        if directory:
            self.save_dir = directory
            self.save_dir_label.setText(f"Diretório de salvamento: {directory}")

    def process_log(self):
        try:
            # Exibir mensagem de processamento
            self.result_text.setText("Processamento iniciado. Aguarde...")
            QApplication.processEvents()

            # Verifica se o arquivo de log e o diretório de salvamento foram selecionados
            if not self.log_file_path or not self.save_dir:
                self.result_text.setText("Por favor, selecione um arquivo de log e um diretório de salvamento.")
                return

            input_file_path = self.log_file_path
            output_dir = tempfile.mkdtemp(prefix='log_filter_output')
            os.makedirs(output_dir, exist_ok=True)

            filter_param = self.filter_param_input.text()
            concat_params = self.concat_params_input.text()

            concat_params_list = []
            if filter_param:
                sanitized_filter_param = sanitize_filename(filter_param.rstrip("/"))
                filtered_file = os.path.join(self.save_dir, f"filtered_{sanitized_filter_param}.log")

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

                self.result_text.setText(f"Processamento concluído. Arquivo de log disponível em {filtered_file}")
                return

            concat_files = []
            if concat_params:
                concat_params_list = [param.strip() for param in concat_params.split(',')]
                for concat_param in concat_params_list:
                    concat_file = concat_requests(input_file_path, output_dir, concat_param)
                    concat_files.append(concat_file)

            all_output_files = filter_urls(input_file_path, output_dir, concat_params_list)

            if not all_output_files and not concat_files:
                self.result_text.setText("Nenhum arquivo foi criado")
                return

            # Realizar auditoria
            missing_lines_file, extra_lines = audit_processed_content(input_file_path, all_output_files + concat_files,
                                                                      output_dir)

            all_output_files.append(missing_lines_file)

            # Gerar checksum
            checksum_log, checksum_content = generate_checksum(input_file_path, all_output_files + concat_files,
                                                               output_dir)
            all_output_files.append(checksum_log)

            zip_filename = f"filtered_{os.path.splitext(os.path.basename(input_file_path))[0]}.zip"
            zip_filepath = create_and_save_zip(all_output_files, concat_files, zip_filename, output_dir)

            if not zip_filepath:
                self.result_text.setText("Falha ao criar o arquivo ZIP")
                return

            final_zip_path = os.path.join(self.save_dir, zip_filename)
            shutil.move(zip_filepath, final_zip_path)

            # Limpar arquivos temporários
            cleanup_files(output_dir, all_output_files, zip_filepath)

            formatted_checksum_content = f"<pre>{checksum_content}</pre>"
            result_message = (f"Processamento concluído.<br>"
                              f"Arquivo ZIP disponível em <a href='{final_zip_path}'>{final_zip_path}</a><br>"
                              f"<br>Checksum:{formatted_checksum_content}")

            self.result_text.setHtml(result_message)

        except Exception as e:
            self.result_text.setText(f"Ocorreu um erro: {e}")


def main():
    app = QApplication(sys.argv)
    window = LogFilterApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
