from .base import Base
from .user import User
from .organization import Organization, OrganizationUser, OrganizationInvitation, PatientFamilyLink, OrganizationUserRole
from .rbac import Role, Permission, RolePermission
from .knowledge import KnowledgeBase, Document, Chunk
from .chat import Conversation, Message, UsageLog
from .api_key import ApiKey
from .patient import PatientProfile
from .manager import ManagerProfile, PatientManagerAssignment, ManagementSuggestion
from .audit import AuditLog

# Ensure all models are in metadata for migrations
__all__ = [
    "User",
    "Organization",
    "OrganizationUser",
    "OrganizationUserRole",
    "OrganizationInvitation",
    "PatientFamilyLink",
    "KnowledgeBase",
    "Document",
    "Chunk",
    "Conversation",
    "Message",
    "UsageLog",
    "ApiKey",
    "PatientProfile",
    "ManagerProfile",
    "PatientManagerAssignment",
    "ManagementSuggestion",
    "AuditLog",
    "Role",
    "Permission",
    "RolePermission"
]
