from PyQt5.QtCore import QThread, pyqtSignal


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