from pathlib import Path


def get_unique_path(base_path):
    """
    Retorna um caminho único, adicionando um número incremental se necessário.
    Exemplo:
    - Se base_path for 'filtered_publish_aemerror_edited' e já existir, retorna 'filtered_publish_aemerror_edited(1)'
    """
    path = Path(base_path)
    if not path.exists():
        return path

    counter = 1
    while True:
        new_path = path.with_name(f"{path.stem}({counter}){path.suffix}")
        if not new_path.exists():
            return new_path
        counter += 1

def format_time(elapsed_time):
    """Formata o tempo decorrido em horas, minutos e segundos."""
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{int(hours)}h {int(minutes)}min {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}min {int(seconds)}s"
    else:
        return f"{int(seconds)}s"