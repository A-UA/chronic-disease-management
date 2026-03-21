import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import boto3

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("JWT_SECRET", "test-secret")

_mock_s3 = MagicMock()
_mock_s3.head_bucket.return_value = {}
boto3.client = MagicMock(return_value=_mock_s3)
