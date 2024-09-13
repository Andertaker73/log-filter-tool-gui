import sys
import re
import tempfile
import shutil
import pythoncom
import os
from win32com.client import Dispatch
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QTextEdit, QGroupBox, QMenuBar, QAction)
from PyQt5.QtGui import QFont
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
        # Inicialização de variáveis
        self.concat_params_inputs = []  # Lista para armazenar os campos de parâmetros de concatenação
        self.log_file_button = None
        self.log_file_label = None
        self.log_file_path = None
        self.filter_param_label = None
        self.filter_param_input = None
        self.save_dir = None
        self.save_dir_label = None
        self.save_dir_button = None
        self.process_button = None
        self.result_text = None
        self.setWindowTitle("Log Filter Tool")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Adiciona o menu
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Ferramentas")

        create_shortcut_action = QAction("Criar Atalho", self)
        create_shortcut_action.triggered.connect(create_bat_file_and_shortcut)
        file_menu.addAction(create_shortcut_action)

        # Grupo para seleção de arquivo
        file_group = QGroupBox("Seleção de Arquivo")
        file_layout = QVBoxLayout()
        self.log_file_button = QPushButton("Selecionar arquivo .log")
        self.log_file_button.setFixedSize(180, 30)
        self.log_file_label = QLabel("Arquivo:")
        self.log_file_button.clicked.connect(self.select_log_file)
        file_layout.addWidget(self.log_file_button)
        file_layout.addWidget(self.log_file_label)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Grupo filter_param
        filter_param_group = QGroupBox("Filtrar por Parâmetro")
        filter_param_layout = QVBoxLayout()
        self.filter_param_label = QLabel("Filtrar por parâmetro (resultará em apenas um log):")
        self.filter_param_input = QLineEdit()
        self.filter_param_input.setPlaceholderText(
            "Ex: /content/b2b-ecommerceequipments-servlets/ecommerceEquipmentWebService./orgUsers/anonymous/carts")
        filter_param_layout.addWidget(self.filter_param_label)
        filter_param_layout.addWidget(self.filter_param_input)
        filter_param_group.setLayout(filter_param_layout)
        layout.addWidget(filter_param_group)

        # Grupo concat_params
        concat_params_group = QGroupBox("Concatenar parâmetros")
        self.concat_params_layout = QVBoxLayout()

        # Botão para adicionar novo campo de parâmetro
        self.add_param_button = QPushButton("Adicionar Parâmetro")
        self.add_param_button.setFixedSize(180, 30)
        self.add_param_button.clicked.connect(self.add_concat_param_field)

        # Adicionar o primeiro campo de parâmetro
        self.add_concat_param_field()

        # Adiciona o botão no final do layout
        self.concat_params_layout.addWidget(self.add_param_button)

        concat_params_group.setLayout(self.concat_params_layout)
        layout.addWidget(concat_params_group)

        # Grupo Salvar Arquivo
        save_file_group = QGroupBox("Salvar resultado")
        save_file_layout = QVBoxLayout()
        self.save_dir_button = QPushButton("Selecionar destino")
        self.save_dir_button.setFixedSize(180, 30)
        self.save_dir_label = QLabel("Destino:")
        self.save_dir_button.clicked.connect(self.select_save_dir)
        save_file_layout.addWidget(self.save_dir_button)
        save_file_layout.addWidget(self.save_dir_label)
        save_file_group.setLayout(save_file_layout)
        layout.addWidget(save_file_group)

        # Grupo para o botão de processamento e resultado
        process_group = QGroupBox("")
        process_layout = QVBoxLayout()
        self.process_button = QPushButton("Processar arquivo")
        self.process_button.setFixedSize(180, 30)
        self.process_button.clicked.connect(self.process_log)
        process_layout.addWidget(self.process_button)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        process_layout.addWidget(self.result_text)

        process_group.setLayout(process_layout)
        layout.addWidget(process_group)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def add_concat_param_field(self):
        new_input = QLineEdit()
        new_input.setPlaceholderText("Ex: URL de parâmetro")

        # Adiciona o novo campo acima do botão "+ Adicionar Parâmetro"
        self.concat_params_layout.insertWidget(self.concat_params_layout.count() - 1, new_input)
        self.concat_params_inputs.append(new_input)

    # def add_concat_param_field(self, layout):
    #     new_input = QLineEdit()
    #     new_input.setPlaceholderText("Ex: URL de parâmetro")
    #     layout.addWidget(new_input)
    #     self.concat_params_inputs.append(new_input)

    def select_log_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo .log")
        if file_name:
            self.log_file_path = file_name
            self.log_file_label.setText(f"Arquivo: {file_name}")

    def select_save_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Salvar em...")
        if directory:
            self.save_dir = directory
            self.save_dir_label.setText(f"Diretório de salvamento: {directory}")

    def process_log(self):
        try:
            self.result_text.setText("Processamento iniciado. Aguarde...")
            QApplication.processEvents()

            if not self.log_file_path or not self.save_dir:
                self.result_text.setText("Por favor, selecione um arquivo de log e um diretório de salvamento.")
                return

            input_file_path = self.log_file_path
            output_dir = tempfile.mkdtemp(prefix='log_filter_output')
            os.makedirs(output_dir, exist_ok=True)

            filter_param = self.filter_param_input.text()
            concat_params_list = [field.text() for field in self.concat_params_inputs if field.text()]

            # Condição 1: Se o filtro por parâmetro estiver preenchido, gera apenas o log filtrado
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

            # Condição 2: Se o filtro por parâmetro não estiver preenchido, gera a totalidade de logs
            all_output_files = filter_urls(input_file_path, output_dir, concat_params_list) if not filter_param else []

            # Condição 3: Se algum campo de concatenação estiver preenchido, realiza a concatenação
            concat_files = []
            if concat_params_list:
                for concat_param in concat_params_list:
                    concat_files.append(concat_requests(input_file_path, output_dir, concat_param))

            if not all_output_files and not concat_files:
                self.result_text.setText("Nenhum arquivo foi criado")
                return

            # Auditoria, checksum e criação do ZIP
            missing_lines_file, extra_lines = audit_processed_content(input_file_path, all_output_files + concat_files,
                                                                      output_dir)
            all_output_files.append(missing_lines_file)
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
