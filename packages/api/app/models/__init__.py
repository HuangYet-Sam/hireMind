"""Import all models so Alembic can detect them."""

from app.models.audit_log import AuditLog  # noqa: F401
from app.models.candidate import Candidate  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.interview import Interview, InterviewFeedback  # noqa: F401
from app.models.matching import Match, MatchFeedback  # noqa: F401
from app.models.offer import Offer, OfferApproval  # noqa: F401
from app.models.position import Position  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
