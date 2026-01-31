import os
import subprocess

from app.ops.accelerator import get_accelerator_status


def transcribe_audio(path: str) -> tuple[str | None, str | None]:
    if not path or not os.path.exists(path):
        return None, "audio_missing"
    status = get_accelerator_status()
    if status.status != "available" or status.throttled:
        return None, status.detail or "accelerator_unavailable"
    cmd_template = os.getenv("CUSTOS_HAILO_WHISPER_CMD", "").strip()
    if not cmd_template:
        return None, "hailo_whisper_cmd_not_configured"
    cmd = cmd_template.format(input=path)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    except Exception as exc:
        return None, f"hailo_whisper_failed:{exc}"
    if result.returncode != 0:
        return None, f"hailo_whisper_failed:{result.stderr.strip() or result.stdout.strip()}"
    output = (result.stdout or "").strip()
    if not output:
        return None, "hailo_whisper_empty"
    return output, None
