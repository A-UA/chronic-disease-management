import os

from snowflake_id_toolkit import TwitterSnowflakeIDGenerator

# Default epoch: 2024-01-01 00:00:00 UTC
DEFAULT_EPOCH = 1704067200000

# Try to get worker id from environment or use a hash of hostname/pid
worker_id = int(os.environ.get("WORKER_ID", 0)) % 1024

# Global instance from third-party library
generator = TwitterSnowflakeIDGenerator(node_id=worker_id, epoch=DEFAULT_EPOCH)


def get_next_id() -> int:
    """
    Generate next Snowflake ID using snowflake-id-toolkit.
    Returns: 64-bit integer
    """
    return generator.generate_next_id()
