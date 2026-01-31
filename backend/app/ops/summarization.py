import json
import os
import tempfile
import subprocess
from typing import Tuple

import httpx

from app.ops.accelerator import get_accelerator_status


def _is_local_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return (
        lowered.startswith('http://127.')
        or lowered.startswith('http://localhost')
        or lowered.startswith('http://192.')
        or lowered.startswith('http://10.')
        or lowered.startswith('http://172.16.')
        or lowered.startswith('http://172.17.')
        or lowered.startswith('http://172.18.')
        or lowered.startswith('http://172.19.')
        or lowered.startswith('http://172.2')
        or lowered.startswith('http://172.30.')
        or lowered.startswith('http://172.31.')
    )


def _hailo_command() -> str | None:
    return os.getenv('CUSTOS_HAILO_SUMMARY_CMD')


def summarize_text(
    text: str,
    provider: str,
    model: str | None,
    max_input_tokens: int | None,
) -> Tuple[str | None, str | None, str | None]:
    if not text:
        return None, 'empty_input', None
    provider = provider or 'hailo'
    max_tokens = max_input_tokens or 2000
    tokens = text.split()
    if len(tokens) > max_tokens:
        text = ' '.join(tokens[:max_tokens])

    if provider == 'home-server':
        url = os.getenv('CUSTOS_HOME_LLM_URL', '')
        if not _is_local_url(url):
            return None, 'home_server_url_invalid', None
        payload = {
            'prompt': text,
            'max_tokens': max_tokens,
            'model': model,
            'mode': 'summary',
        }
        try:
            response = httpx.post(url, json=payload, timeout=60)
        except Exception as exc:
            return None, f'home_server_error:{exc}', None
        if response.status_code != 200:
            return None, f'home_server_error:{response.status_code}', None
        try:
            data = response.json()
        except json.JSONDecodeError:
            return None, 'home_server_invalid_json', None
        summary = data.get('summary') or data.get('text') or data.get('response')
        return summary, None if summary else 'home_server_empty', model

    status = get_accelerator_status()
    if status.status != 'available':
        return None, status.detail or 'accelerator_unavailable', model

    cmd = _hailo_command()
    if not cmd:
        return None, 'hailo_command_missing', model
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.txt')
            output_path = os.path.join(tmpdir, 'summary.txt')
            with open(input_path, 'w', encoding='utf-8') as handle:
                handle.write(text)
            rendered = cmd.replace('{input}', input_path).replace('{output}', output_path).replace('{model}', model or '')
            result = subprocess.run(rendered, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                return None, f'hailo_error:{result.stderr.strip() or result.stdout.strip()}', model
            if not os.path.exists(output_path):
                return None, 'hailo_output_missing', model
            with open(output_path, 'r', encoding='utf-8') as handle:
                summary = handle.read().strip()
            return summary, None if summary else 'hailo_empty', model
    except Exception as exc:
        return None, f'hailo_error:{exc}', model
