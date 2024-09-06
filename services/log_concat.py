import os
import re

from services.log_filter import sanitize_filename


def concat_requests(input_file, output_dir, concat_param):
    sanitized_base_name = sanitize_filename(concat_param.rstrip("/"))
    output_file = os.path.join(output_dir, f"{sanitized_base_name}.log")

    with open(input_file, 'r', encoding='utf-8') as log_origin, open(output_file, 'w', encoding='utf-8') as concat_file:
        capture_lines = False
        for line in log_origin:
            if concat_param in line:
                concat_file.write(line)
                capture_lines = '*ERROR*' in line
            elif capture_lines:
                timestamp_match = re.match(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}', line)
                if not timestamp_match:
                    concat_file.write(line)
                else:
                    capture_lines = False

    return output_file