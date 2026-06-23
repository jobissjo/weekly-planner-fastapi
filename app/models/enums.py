import enum

class UserRole(str, enum.Enum):
    ADMIN = 'admin'
    USER = 'user'

class EmailType(str, enum.Enum):
    SMTP = 'smtp'
    MSAL = 'msal'

class TaskPriority(str, enum.Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

class TaskStatus(str, enum.Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    SKIPPED = 'skipped'