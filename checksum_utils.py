import os


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

    # Criar o relatório de checksum
    checksum_log = os.path.join(output_dir, "checksum.log")
    with open(checksum_log, 'w', encoding='utf-8') as log:
        log.write(f"Linhas arquivo original: {original_line_count}\n")
        log.write(f"Linhas processadas: {processed_line_count}\n")
        log.write(f"Caracteres totais arquivo original: {original_char_count}\n")
        log.write(f"Caracteres totais processados: {processed_char_count}\n")

    print(f"Relatório de checksum criado em {checksum_log}")

    return checksum_log