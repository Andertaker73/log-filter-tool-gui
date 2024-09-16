import pythoncom

from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from win32com.client import Dispatch


def create_bat_file_and_shortcut():
    project_dir = Path(__file__).resolve().parent.parent
    bat_file_path = project_dir / 'run_log_filter_tool.bat'

    bat_content = f'''@echo off
    cd /d {project_dir}
    call .venv\\Scripts\\activate
    pythonw main.py
    deactivate
    '''

    with bat_file_path.open('w') as bat_file:
        bat_file.write(bat_content)

    shortcut_dir = QFileDialog.getExistingDirectory(None, "Selecionar diretório para salvar o atalho")

    if shortcut_dir:
        shortcut_dir = Path(shortcut_dir)
        shortcut_path = shortcut_dir / 'Atalho - LogFilterTool.lnk'

        pythoncom.CoInitialize()
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))

        shortcut.TargetPath = str(bat_file_path)
        shortcut.WorkingDirectory = str(project_dir)
        shortcut.WindowStyle = 7
        shortcut.save()

        # Exibe o caminho corretamente formatado conforme o sistema operacional
        formatted_path = shortcut_path.as_posix() if not shortcut_path.is_absolute() else str(shortcut_path)
        return True, QMessageBox.information(None, "Sucesso", f"Atalho criado com sucesso!\n"
                                                              f"Caminho: {formatted_path}")
    else:
        return False, QMessageBox.warning(None, "Erro", "Não foi possível criar o atalho. Por favor, tente novamente.")
