# checksum_utils.py

import os
import texttable as tt  # Biblioteca para formatar o "quadro"

def generate_checksum(input_file, all_output_files, output_dir):
    original_line_count = 0
    original_char_count = 0
    processed_line_count = 0
    processed_char_count = 0

    # Contar as linhas e caracteres do arquivo original
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            original_line_count += 1
            original_char_count += len(line)

    # Contar as linhas e caracteres dos arquivos processados
    for processed_file in all_output_files:
        with open(processed_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed_line_count += 1
                processed_char_count += len(line)

    # Calcular a diferença entre o arquivo original e os processados
    line_difference = original_line_count - processed_line_count
    char_difference = original_char_count - processed_char_count

    # Criar um "quadro" de dados para o checksum
    table = tt.Texttable()
    table.set_cols_align(["c", "c", "c", "c"])  # Alinhamento das colunas
    table.set_cols_valign(["m", "m", "m", "m"])  # Alinhamento vertical
    table.set_cols_dtype(["t", "i", "i", "i"])  # Tipos de dados: texto, inteiro, inteiro, inteiro

    # Adicionar as linhas do quadro
    table.add_rows([["Descrição", "Valor Original", "Valor Processado", "Diferença"],
                    ["Linhas", original_line_count, processed_line_count, line_difference],
                    ["Caracteres", original_char_count, processed_char_count, char_difference]])

    # Obter o conteúdo formatado do quadro
    checksum_content = table.draw()

    # Salvar o relatório de checksum no arquivo
    checksum_log = os.path.join(output_dir, "checksum.log")
    with open(checksum_log, 'w', encoding='utf-8') as log:
        log.write(checksum_content)

    print(f"Relatório de checksum criado em {checksum_log}")

    return checksum_log
