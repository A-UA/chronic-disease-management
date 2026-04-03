import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import boto3

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 测试环境必需的环境变量
os.environ.setdefault("JWT_SECRET", "test-secret-for-chronic-disease-management-2026")
os.environ.setdefault("API_KEY_SALT", "test-salt-for-chronic-disease-management-2026")

# Mock boto3（避免真实连接 MinIO）
_mock_s3 = MagicMock()
_mock_s3.head_bucket.return_value = {}
boto3.client = MagicMock(return_value=_mock_s3)
