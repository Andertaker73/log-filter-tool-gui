# checksum_utils.py

import os
import texttable as tt  # Biblioteca para formatar o "quadro"

def generate_checksum(input_file, all_output_files, output_dir):
    original_line_count = 0
    original_char_count = 0
    processed_line_count = 0
    processed_char_count = 0

    # Inicializar contadores para expressões
    original_debug_count = 0
    original_info_count = 0
    original_error_count = 0
    original_warn_count = 0

    processed_debug_count = 0
    processed_info_count = 0
    processed_error_count = 0
    processed_warn_count = 0

    # Contar as linhas, caracteres e ocorrências das expressões no arquivo original
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            original_line_count += 1
            original_char_count += len(line)
            # Contagem de expressões no arquivo original
            if '*DEBUG*' in line:
                original_debug_count += 1
            if '*INFO*' in line:
                original_info_count += 1
            if '*ERROR*' in line:
                original_error_count += 1
            if '*WARN*' in line:
                original_warn_count += 1

    # Contar as linhas, caracteres e ocorrências das expressões nos arquivos processados
    for processed_file in all_output_files:
        with open(processed_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed_line_count += 1
                processed_char_count += len(line)
                # Contagem de expressões nos arquivos processados
                if '*DEBUG*' in line:
                    processed_debug_count += 1
                if '*INFO*' in line:
                    processed_info_count += 1
                if '*ERROR*' in line:
                    processed_error_count += 1
                if '*WARN*' in line:
                    processed_warn_count += 1

    # Calcular a diferença entre o arquivo original e os processados
    line_difference = original_line_count - processed_line_count
    char_difference = original_char_count - processed_char_count
    debug_difference = original_debug_count - processed_debug_count
    info_difference = original_info_count - processed_info_count
    error_difference = original_error_count - processed_error_count
    warn_difference = original_warn_count - processed_warn_count

    # Criar um "quadro" de dados para o checksum
    table = tt.Texttable()
    table.set_cols_align(["c", "c", "c", "c"])  # Alinhamento das colunas
    table.set_cols_valign(["m", "m", "m", "m"])  # Alinhamento vertical
    table.set_cols_dtype(["t", "i", "i", "i"])  # Tipos de dados: texto, inteiro, inteiro, inteiro

    # Adicionar as linhas do quadro
    table.add_rows([["Descrição", "Arquivo Original", "Arquivos Processados", "Diferença"],
                    ["DEBUG", original_debug_count, processed_debug_count, debug_difference],
                    ["INFO", original_info_count, processed_info_count, info_difference],
                    ["ERROR", original_error_count, processed_error_count, error_difference],
                    ["WARN", original_warn_count, processed_warn_count, warn_difference],
                    ["Linhas Totais", original_line_count, processed_line_count, line_difference],
                    ["Caracteres Totais", original_char_count, processed_char_count, char_difference]])

    # Obter o conteúdo formatado do quadro
    checksum_content = table.draw()

    # Salvar o relatório de checksum no arquivo
    checksum_log = os.path.join(output_dir, "checksum.log")
    with open(checksum_log, 'w', encoding='utf-8') as log:
        log.write(checksum_content)

    print(f"Relatório de checksum criado em {checksum_log}")

    return checksum_log
