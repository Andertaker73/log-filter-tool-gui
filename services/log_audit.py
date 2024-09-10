import os


def audit_processed_content(input_file, all_output_files, output_dir):
    input_lines_dict = {}
    processed_lines_dict = {}

    # Contar as ocorrências de cada linha no arquivo original
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            input_lines_dict[line] = input_lines_dict.get(line, 0) + 1

    # Contar as ocorrências de cada linha nos arquivos processados
    for processed_file in all_output_files:
        with open(processed_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed_lines_dict[line] = processed_lines_dict.get(line, 0) + 1

    missing_lines = []
    extra_lines = 0

    # Identificar e registrar as linhas que estão faltando no processamento
    for line, count in input_lines_dict.items():
        if line not in processed_lines_dict or processed_lines_dict[line] < count:
            missing_count = count - processed_lines_dict.get(line, 0)
            for _ in range(missing_count):
                missing_lines.append(line)

    # Registrar as linhas que foram processadas em excesso (possível duplicação ou erro)
    for line, count in processed_lines_dict.items():
        if line not in input_lines_dict:
            extra_lines += count
        elif processed_lines_dict[line] > input_lines_dict[line]:
            extra_lines += (processed_lines_dict[line] - input_lines_dict[line])

    # Criar o relatório detalhado das linhas faltantes
    missing_lines_file = os.path.join(output_dir, "aem_processes.log")
    with open(missing_lines_file, 'w', encoding='utf-8') as log:
        for line in missing_lines:
            log.write(line)

    print(f"Relatório de linhas faltantes criado em {missing_lines_file}")

    return missing_lines_file, extra_lines