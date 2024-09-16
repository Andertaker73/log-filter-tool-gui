import sys
import re
import os
import time

from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QLabel,
                             QLineEdit, QTextEdit, QGroupBox, QAction)
from services.checksum import generate_checksum
from services.log_audit import audit_processed_content
from services.log_concat import concat_requests
from services.log_filter import sanitize_filename, filter_urls
from services.shortcut_creator import create_bat_file_and_shortcut
from services.utils import get_unique_path, format_time


class LogProcessingThread(QThread):
    progress = pyqtSignal(str)

    def __init__(self, input_file_path, filter_param, concat_params_list, save_dir, log_filter_callback):
        super().__init__()
        self.input_file_path = input_file_path
        self.filter_param = filter_param
        self.concat_params_list = concat_params_list
        self.save_dir = save_dir
        self.log_filter_callback = log_filter_callback

    def run(self):
        try:
            result_message = self.log_filter_callback(self.input_file_path, self.filter_param, self.concat_params_list, self.save_dir)
            self.progress.emit(result_message)
        except Exception as e:
            self.progress.emit(f"Ocorreu um erro: {e}")

class LogFilterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Inicialização de variáveis
        self.processing_thread = None
        self.log_file_button = None
        self.log_file_label = None
        self.log_file_path = None
        self.filter_param_label = None
        self.filter_param_input = None
        self.concat_params_layout = None
        self.concat_params_inputs = []
        self.add_param_button = None
        self.save_dir = None
        self.save_dir_label = None
        self.save_dir_button = None
        self.start_time = None
        self.timer = None
        self.process_button = None
        self.result_text = None
        self.setWindowTitle("Log Filter Tool")
        self.setGeometry(100, 100, 800, 800)
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
        filter_param_group = QGroupBox("Filtrar")
        filter_param_layout = QVBoxLayout()
        self.filter_param_label = QLabel("Por parâmetro (resultará em apenas um log):")
        self.filter_param_input = QLineEdit()
        self.filter_param_input.setPlaceholderText(
            "Ex: /content/b2b-ecommerceequipments-servlets/ecommerceEquipmentWebService./orgUsers")
        filter_param_layout.addWidget(self.filter_param_label)
        filter_param_layout.addWidget(self.filter_param_input)
        filter_param_group.setLayout(filter_param_layout)
        layout.addWidget(filter_param_group)

        # Grupo concat_params
        concat_params_group = QGroupBox("Concatenar relatórios")
        self.concat_params_layout = QVBoxLayout()

        # Botão para adicionar novo campo de parâmetro
        self.add_param_button = QPushButton("Adicionar parâmetro")
        self.add_param_button.setFixedSize(180, 30)
        self.add_param_button.clicked.connect(self.add_concat_param_field)

        # Adicionar o primeiro campo de parâmetro
        self.add_concat_param_field()

        # Adiciona o botão no final do layout
        self.concat_params_layout.addWidget(self.add_param_button)

        concat_params_group.setLayout(self.concat_params_layout)
        layout.addWidget(concat_params_group)

        # Grupo Salvar Resultado
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
        new_input.setPlaceholderText("Ex: content/b2b-ecommerceequipments-servlets/ecommerceEquipmentWebService./orgUsers/anonymous/orgUnits")

        # Adiciona o novo campo acima do botão "Adicionar Parâmetro"
        self.concat_params_layout.insertWidget(self.concat_params_layout.count() - 1, new_input)
        self.concat_params_inputs.append(new_input)

    def select_log_file(self):
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo .log", downloads_path)
        if file_name:
            self.log_file_path = file_name
            self.log_file_label.setText(f"Arquivo: <span style='color:blue'>{file_name}</span>")

    def select_save_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Salvar em...")
        if directory:
            self.save_dir = directory
            self.save_dir_label.setText(f"Destino: <span style='color:blue'>{directory}</span>")

    def update_elapsed_time(self):
        """Atualiza o tempo decorrido na interface a cada segundo."""
        elapsed_time = time.time() - self.start_time
        formatted_time = format_time(elapsed_time)
        self.result_text.setText(f"Processamento iniciado. Aguarde...<br>Tempo decorrido: {formatted_time}")
        QApplication.processEvents()

    def on_processing_finished(self, result_message):
        self.result_text.setHtml(result_message)
        self.timer.stop()

    def process_log(self):
        try:
            self.result_text.setText("Processamento iniciado. Aguarde...")
            QApplication.processEvents()

            if not self.log_file_path or not self.save_dir:
                self.result_text.setText(
                    "<span style='color: red'>Por favor, selecione um arquivo de log e um diretório de salvamento.<span>")
                return

            # Inicia o cronômetro e o timer para exibição do tempo decorrido em tempo real
            self.start_time = time.time()
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_elapsed_time)
            self.timer.start(1000)

            input_file_path = self.log_file_path
            filter_param = self.filter_param_input.text().strip()
            concat_params_list = [field.text().strip() for field in self.concat_params_inputs if field.text()]

            # Inicia o processamento em uma thread separada
            self.processing_thread = LogProcessingThread(input_file_path, filter_param, concat_params_list, self.save_dir, self.perform_log_processing)
            self.processing_thread.progress.connect(self.on_processing_finished)
            self.processing_thread.start()

        except Exception as e:
            self.result_text.setText(f"Ocorreu um erro: {e}")

    def perform_log_processing(self, input_file_path, filter_param, concat_params_list, save_dir):
        # Se o filtro por parâmetro estiver preenchido, gera apenas o log filtrado
        if filter_param:
            sanitized_filter_param = sanitize_filename(filter_param.rstrip("/"))
            filtered_file = get_unique_path(Path(save_dir) / f"filtered_{sanitized_filter_param}.log")

            with open(input_file_path, 'r', encoding='utf-8') as log_origin, open(filtered_file, 'w', encoding='utf-8') as out_file:
                capture_lines = False
                for line in log_origin:
                    if filter_param in line:
                        out_file.write(line)
                        capture_lines = '*ERROR*' in line
                    elif capture_lines:
                        timestamp_match = re.match(r'\d{2}\.\d{2}\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                        if not timestamp_match:
                            out_file.write(line)
                        else:
                            capture_lines = False

            elapsed_time = time.time() - self.start_time
            formatted_time = format_time(elapsed_time)
            return (f"Processamento concluído.<br>Tempo decorrido: {formatted_time}<br>"
                    f"Arquivo de log disponível em:<br><a href='{filtered_file}'>{filtered_file}</a><br>")

        # SE o filtro por parâmetro NÃO estiver preenchido, gera a totalidade de logs e cria a pasta
        log_filename = Path(input_file_path).stem
        output_dir = get_unique_path(Path(save_dir) / f"filtered_{log_filename}")
        output_dir.mkdir(parents=True, exist_ok=True)

        all_output_files = filter_urls(input_file_path, output_dir, concat_params_list)

        # Se algum campo de concatenação estiver preenchido, realiza a concatenação
        concat_files = []
        if concat_params_list:
            for concat_param in concat_params_list:
                concat_files.append(concat_requests(input_file_path, output_dir, concat_param))

        if not all_output_files and not concat_files:
            return "Nenhum arquivo foi criado"

        missing_lines_file, extra_lines = audit_processed_content(input_file_path, all_output_files + concat_files, output_dir)
        all_output_files.append(missing_lines_file)
        checksum_log, checksum_content = generate_checksum(input_file_path, all_output_files + concat_files, output_dir)
        all_output_files.append(checksum_log)

        elapsed_time = time.time() - self.start_time
        formatted_time = format_time(elapsed_time)
        formatted_checksum_content = f"<pre>{checksum_content}</pre>"
        return (f"Processamento concluído.<br>Tempo decorrido: {formatted_time}<br>"
                f"Arquivo está disponível em:<br><a href='{output_dir}'>{output_dir}</a><br><br>"
                f"Checksum:{formatted_checksum_content}")


def main():
    app = QApplication(sys.argv)
    window = LogFilterApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
