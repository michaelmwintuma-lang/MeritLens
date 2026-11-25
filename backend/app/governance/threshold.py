"""
Company-configured promotion threshold policy.
Allows company Admins and HR specialists to adjust the promotion recommendation cut-off
from the default machine learning F1-optimal threshold (0.2283) to an organization-specific policy.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.governance.models import ThresholdPolicy

_CACHED_CUSTOM_THRESHOLD: float | None = None
_CACHE_INITIALIZED: bool = False


def now() -> datetime:
    return datetime.now(timezone.utc)


def clear_cache() -> None:
    global _CACHE_INITIALIZED, _CACHED_CUSTOM_THRESHOLD
    _CACHE_INITIALIZED = False
    _CACHED_CUSTOM_THRESHOLD = None


def get_policy(db: Session) -> ThresholdPolicy:
    """Return the threshold policy row (id=1), creating it if it doesn't exist."""
    policy = db.get(ThresholdPolicy, 1)
    if policy is None:
        policy = ThresholdPolicy(id=1, custom_threshold=None, updated_at=now(), updated_by_name="System Default")
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy


def get_active_custom_threshold() -> float | None:
    """Return the in-memory cached custom threshold, or query the DB once if not loaded."""
    global _CACHE_INITIALIZED, _CACHED_CUSTOM_THRESHOLD
    if not _CACHE_INITIALIZED:
        try:
            from app.core.database import SessionLocal
            with SessionLocal() as db:
                policy = db.get(ThresholdPolicy, 1)
                _CACHED_CUSTOM_THRESHOLD = policy.custom_threshold if policy else None
        except Exception:
            _CACHED_CUSTOM_THRESHOLD = None
        _CACHE_INITIALIZED = True
    return _CACHED_CUSTOM_THRESHOLD


def set_custom_threshold(db: Session, threshold_val: float | None, user_name: str | None = None) -> ThresholdPolicy:
    """Update or reset the company-configured threshold."""
    global _CACHE_INITIALIZED, _CACHED_CUSTOM_THRESHOLD
    policy = get_policy(db)
    policy.custom_threshold = threshold_val
    policy.updated_at = now()
    policy.updated_by_name = user_name
    db.commit()
    db.refresh(policy)
    _CACHED_CUSTOM_THRESHOLD = threshold_val
    _CACHE_INITIALIZED = True
    return policy
