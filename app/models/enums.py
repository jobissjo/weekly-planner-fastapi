import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class EmailType(str, enum.Enum):
    SMTP = "smtp"
    MSAL = "msal"


class TaskPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class FeedbackType(str, enum.Enum):
    CONTACT = "contact"
    REPORT = "report"
    SUGGESTION = "suggestion"
    APPRECIATION = "appreciation"
    FEEDBACK = "feedback"


class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
