import os
import shutil
import time


def cleanup_files(output_dir, all_output_files, zip_filepath):
    time.sleep(2)  # Pausa para garantir que outros processos concluam o uso dos arquivos
    try:
        # Tentar remover cada arquivo temporário
        for file in all_output_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    print(f"Arquivo temporário excluído: {file}")
                except Exception as e:
                    print(f"Erro ao excluir o arquivo {file}: {e}")

        # Tentar remover o arquivo ZIP
        if os.path.exists(zip_filepath):
            try:
                os.remove(zip_filepath)
                print(f"Arquivo ZIP excluído: {zip_filepath}")
            except Exception as e:
                print(f"Erro ao excluir o arquivo ZIP {zip_filepath}: {e}")

        # Tentar remover o diretório temporário
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
                print(f"Diretório temporário excluído: {output_dir}")
            except Exception as e:
                print(f"Erro ao excluir o diretório {output_dir}: {e}")

    except Exception as e:
        print(f"Falha na limpeza: {e}")