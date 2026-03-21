import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.rag_evaluation import evaluate_rag_cases


def main() -> None:
    fixture_path = ROOT / "tests" / "fixtures" / "rag_cases.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    summary = evaluate_rag_cases(cases, k=5)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
