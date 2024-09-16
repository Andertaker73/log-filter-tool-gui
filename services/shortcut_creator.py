import os
import pythoncom

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from win32com.client import Dispatch


def create_bat_file_and_shortcut():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    bat_file_path = os.path.join(project_dir, 'run_log_filter_tool.bat')

    bat_content = '''@echo off
    cd /d {project_dir}
    call .venv\\Scripts\\activate
    pythonw main.py
    deactivate
    '''.format(project_dir=project_dir)

    with open(bat_file_path, 'w') as bat_file:
        bat_file.write(bat_content)

    shortcut_dir = QFileDialog.getExistingDirectory(None, "Selecionar diretório para salvar o atalho")

    if shortcut_dir:
        shortcut_path = os.path.join(shortcut_dir, 'Atalho - LogFilterTool.lnk')

        pythoncom.CoInitialize()
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)

        shortcut.TargetPath = bat_file_path
        shortcut.WorkingDirectory = project_dir
        shortcut.WindowStyle = 7
        shortcut.save()

        QMessageBox.information(None, "Sucesso", f"Atalho criado!<br>"
                                                 f"Caminho: {shortcut_path}")
        return True
    else:
        QMessageBox.warning(None, "Erro", "Não foi possível criar o atalho. Por favor, tente novamente.")
        return False
