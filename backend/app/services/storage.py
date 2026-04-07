"""Storage service - compat export layer (remove in phase 6)

All logic moved to app.core.storage
"""
from app.core.storage import StorageService, get_storage_service, _sanitize_filename  # noqa: F401
