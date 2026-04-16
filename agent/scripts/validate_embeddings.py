import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.embedding_validation import validate_embedding_provider
from app.services.embeddings import get_embedding_provider


def main() -> None:
    provider = get_embedding_provider()
    result = validate_embedding_provider(provider, sample_text="血糖高怎么办？")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
