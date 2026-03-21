import json
import subprocess
import sys
from pathlib import Path


def test_evaluate_rag_script_outputs_metrics_json():
    backend_dir = Path(__file__).resolve().parents[2]
    script_path = backend_dir / "scripts" / "evaluate_rag.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["case_count"] == 2
    assert "recall_at_k" in payload["metrics"]
