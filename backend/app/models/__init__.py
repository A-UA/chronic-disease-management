from .api_key import ApiKey
from .audit import AuditLog
from .base import Base
from .chat import Conversation, Message, UsageLog
from .health_metric import HealthMetric
from .knowledge import Chunk, Document, KnowledgeBase
from .manager import ManagementSuggestion, ManagerProfile, PatientManagerAssignment
from .menu import Menu
from .organization import (
    Organization,
    OrganizationInvitation,
    OrganizationUser,
    OrganizationUserRole,
    PatientFamilyLink,
)
from .patient import PatientProfile
from .rbac import Action, Permission, Resource, Role, RoleConstraint, RolePermission
from .settings import SystemSetting
from .tenant import Tenant
from .user import PasswordResetToken, User

# Ensure all models are in metadata for migrations
__all__ = [
    "Base",
    "HealthMetric",
    "PasswordResetToken",
    "Tenant",
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
    "SystemSetting",
    "Role",
    "Permission",
    "RolePermission",
    "Resource",
    "Action",
    "RoleConstraint",
    "Menu",
]
