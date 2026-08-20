"""Internal token wallet: lazy create, grants, and audited ledger."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.marketplace import WalletLedgerKind
from app.models.user import User
from app.models.user_wallet import UserWallet
from app.models.wallet_ledger import WalletLedger


class WalletError(AppError):
    pass


def get_or_create_wallet(db: Session, *, user_id: uuid.UUID) -> UserWallet:
    wallet = db.get(UserWallet, user_id)
    if wallet is not None:
        return wallet
    wallet = UserWallet(user_id=user_id, balance=0)
    db.add(wallet)
    db.flush()
    return wallet


def get_wallet_for_update(db: Session, *, user_id: uuid.UUID) -> UserWallet:
    get_or_create_wallet(db, user_id=user_id)
    wallet = db.scalar(
        select(UserWallet).where(UserWallet.user_id == user_id).with_for_update()
    )
    assert wallet is not None
    return wallet


def apply_ledger_delta(
    db: Session,
    *,
    user_id: uuid.UUID,
    delta: int,
    kind: WalletLedgerKind | str,
    pack_id: uuid.UUID | None = None,
    note: str | None = None,
    created_by: uuid.UUID | None = None,
) -> tuple[UserWallet, WalletLedger]:
    if delta == 0:
        raise WalletError(
            "Wallet delta must be non-zero",
            code=ErrorCode.WALLET_GRANT_INVALID,
        )
    kind_value = kind.value if isinstance(kind, WalletLedgerKind) else kind
    wallet = get_wallet_for_update(db, user_id=user_id)
    next_balance = wallet.balance + delta
    if next_balance < 0:
        raise WalletError(
            "Insufficient tokens",
            code=ErrorCode.INSUFFICIENT_TOKENS,
            status_code=402,
            params={
                "balance": str(wallet.balance),
                "required": str(abs(delta)),
            },
        )
    wallet.balance = next_balance
    entry = WalletLedger(
        user_id=user_id,
        delta=delta,
        balance_after=next_balance,
        kind=kind_value,
        pack_id=pack_id,
        note=note,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()
    return wallet, entry


def grant_tokens(
    db: Session,
    *,
    user_id: uuid.UUID,
    amount: int,
    note: str | None = None,
    created_by: uuid.UUID | None = None,
) -> tuple[UserWallet, WalletLedger]:
    if amount <= 0:
        raise WalletError(
            "Grant amount must be positive",
            code=ErrorCode.WALLET_GRANT_INVALID,
            params={"amount": str(amount)},
        )
    target = db.get(User, user_id)
    if target is None:
        raise WalletError(
            "User not found",
            code=ErrorCode.USER_NOT_FOUND,
            status_code=404,
        )
    return apply_ledger_delta(
        db,
        user_id=user_id,
        delta=amount,
        kind=WalletLedgerKind.GRANT,
        note=note,
        created_by=created_by,
    )


def list_ledger(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[WalletLedger]:
    return list(
        db.scalars(
            select(WalletLedger)
            .where(WalletLedger.user_id == user_id)
            .order_by(WalletLedger.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
