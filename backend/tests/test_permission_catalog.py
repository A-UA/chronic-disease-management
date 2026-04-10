from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = ROOT / "app" / "seed.py"
ROUTERS_DIR = ROOT / "app" / "routers"
CHECK_PERMISSION_PATTERN = re.compile(r'check_permission\("([^"]+)"\)')


def _load_seeded_permissions() -> set[str]:
    module = ast.parse(SEED_FILE.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PERMISSION_MAP":
                    permission_map = ast.literal_eval(node.value)
                    return {
                        f"{resource}:{action}"
                        for resource, action, *_ in permission_map
                    }
    raise AssertionError("PERMISSION_MAP not found in seed.py")


def _load_route_permission_codes() -> set[str]:
    codes: set[str] = set()
    for path in ROUTERS_DIR.rglob("*.py"):
        matches = CHECK_PERMISSION_PATTERN.findall(path.read_text(encoding="utf-8"))
        codes.update(matches)
    return codes


def test_all_route_permission_codes_exist_in_seed_catalog() -> None:
    seeded_permissions = _load_seeded_permissions()
    route_permissions = _load_route_permission_codes()

    missing = sorted(route_permissions - seeded_permissions)

    assert missing == [], (
        "Route permission codes must exist in app.seed.PERMISSION_MAP. "
        f"Missing: {missing}"
    )
