import os
import shutil
import time


def cleanup_files(output_dir, all_output_files, zip_filepath):
    time.sleep(2)
    try:
        for file in all_output_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"Arquivo temporário excluído: {file}")
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
            print(f"Arquivo ZIP excluído: {zip_filepath}")
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            print(f"Diretório temporário excluído: {output_dir}")
    except Exception as e:
        print(f"Falha na limpeza: {e}")