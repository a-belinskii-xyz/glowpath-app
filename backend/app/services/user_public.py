from app.core.feature_flags import features_for_user
from app.models.user import User
from app.schemas.user import UserPublic
from app.services.billing_service import plan_state_for_user


def to_user_public(user: User) -> UserPublic:
    state = plan_state_for_user(user)
    return UserPublic(
        id=user.id,
        email=user.email,
        timezone=user.timezone,
        email_verified=user.email_verified_at is not None,
        email_verified_at=user.email_verified_at,
        onboarding_completed=user.onboarding_completed_at is not None,
        onboarding_completed_at=user.onboarding_completed_at,
        has_password=user.password_hash is not None,
        features=features_for_user(user),
        plan=state.slug,
        entitlements=sorted(state.entitlements),
    )
