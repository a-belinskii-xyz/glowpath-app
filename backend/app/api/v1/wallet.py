"""Internal token wallet API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.marketplace import (
    WalletGrantBody,
    WalletLedgerEntryPublic,
    WalletLedgerListResponse,
    WalletPublic,
)
from app.services.wallet_service import (
    WalletError,
    get_or_create_wallet,
    grant_tokens,
    list_ledger,
)

router = APIRouter(tags=["wallet"])


def _require_wallet(user: User) -> None:
    # Tokens are spent only in the marketplace, so the wallet follows its flag.
    if not is_feature_enabled_for_user(FeatureFlag.ICON_MARKETPLACE, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code=ErrorCode.MARKETPLACE_DISABLED,
                message="Wallet is not enabled for this user",
            ),
        )


def _require_staff(user: User) -> None:
    if not user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code=ErrorCode.STAFF_REQUIRED,
                message="Staff access required",
            ),
        )


@router.get("", response_model=WalletPublic)
def get_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WalletPublic:
    _require_wallet(current_user)
    wallet = get_or_create_wallet(db, user_id=current_user.id)
    db.commit()
    return WalletPublic(balance=wallet.balance)


@router.get("/ledger", response_model=WalletLedgerListResponse)
def get_wallet_ledger(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WalletLedgerListResponse:
    _require_wallet(current_user)
    entries = list_ledger(db, user_id=current_user.id, limit=limit, offset=offset)
    return WalletLedgerListResponse(
        items=[
            WalletLedgerEntryPublic(
                id=entry.id,
                delta=entry.delta,
                balance_after=entry.balance_after,
                kind=entry.kind,
                pack_id=entry.pack_id,
                note=entry.note,
                created_at=entry.created_at,
            )
            for entry in entries
        ]
    )


@router.post("/staff/grants", response_model=WalletPublic)
def post_staff_grant(
    body: WalletGrantBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WalletPublic:
    _require_wallet(current_user)
    _require_staff(current_user)
    try:
        wallet, _entry = grant_tokens(
            db,
            user_id=body.user_id,
            amount=body.amount,
            note=body.note,
            created_by=current_user.id,
        )
        db.commit()
    except WalletError as exc:
        db.rollback()
        raise_http_error(exc)
        raise
    return WalletPublic(balance=wallet.balance)
