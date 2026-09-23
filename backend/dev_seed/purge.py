from __future__ import annotations

import uuid

from app.config import settings
from app.models.user import User
from minio import Minio
from minio.error import S3Error
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from dev_seed.config import SEED_EMAIL_DOMAIN
from dev_seed.personas import seed_emails


def _minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def delete_user_prefix(user_id: uuid.UUID) -> int:
    """Remove all MinIO objects under `{user_id}/`. Returns deleted count."""
    client = _minio_client()
    bucket = settings.minio_bucket
    prefix = f"{user_id}/"
    deleted = 0
    try:
        if not client.bucket_exists(bucket):
            return 0
        for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
            if obj.object_name:
                client.remove_object(bucket, obj.object_name)
                deleted += 1
    except S3Error as exc:
        raise RuntimeError(f"Failed to purge MinIO prefix {prefix}: {exc}") from exc
    return deleted


def purge_seed_users(db: Session, *, user_count: int | None = None) -> tuple[int, int]:
    """
    Delete known seed users (and cascade DB rows) plus their MinIO prefixes.

    Uses Core DELETE so PostgreSQL ON DELETE CASCADE runs; ORM session.delete()
    would try to NULL mood_entries.user_id and fail the NOT NULL constraint.

    Returns (users_deleted, objects_deleted).
    """
    emails = seed_emails(count=user_count)
    stmt = select(User.id).where(
        or_(
            User.email.in_(emails),
            User.email.like(f"%@{SEED_EMAIL_DOMAIN}"),
            # Legacy domain from earlier drafts
            User.email.like("%@seed.local"),
        )
    )
    user_ids = list(db.scalars(stmt).all())
    objects_deleted = 0
    for user_id in user_ids:
        objects_deleted += delete_user_prefix(user_id)

    if user_ids:
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.flush()

    return len(user_ids), objects_deleted
