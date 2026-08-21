"""Wallet ledger ops: grants, adjustments, reconcile, pack refunds."""

from __future__ import annotations

import uuid

import pytest
from app.cli.wallet import build_parser
from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.marketplace import PackStatus, WalletLedgerKind
from app.models.icon_pack import IconPack
from app.models.icon_pack_unlock import IconPackUnlock
from app.services.marketplace_service import (
    MarketplaceError,
    revoke_pack_unlock,
    unlock_pack,
)
from app.services.wallet_service import (
    WalletError,
    adjust_tokens,
    get_or_create_wallet,
    grant_tokens,
    ledger_total,
    list_ledger,
    reconcile_wallet_ledger,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login
from tests.test_marketplace import _user_from_token


@pytest.fixture(autouse=True)
def _enable_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_icon_marketplace", True)
    monkeypatch.setattr(settings, "feature_icon_marketplace_percent", 100)


def _published_pack(db: Session, *, price: int) -> IconPack:
    pack = IconPack(
        slug=f"ops-{uuid.uuid4().hex[:12]}",
        is_official=True,
        status=PackStatus.PUBLISHED.value,
        price_tokens=price,
        labels={"name": {"en": "Ops pack", "ru": "Опс-пак"}},
    )
    db.add(pack)
    db.flush()
    return pack


def test_cli_parser_requires_note_and_user() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["grant", "--user", "a@example.com", "--amount", "10"])
    args = parser.parse_args(
        ["grant", "--user", "a@example.com", "--amount", "10", "--note", "beta"]
    )
    assert args.command == "grant"
    assert args.amount == 10
    revoke = parser.parse_args(
        [
            "revoke",
            "--user",
            "a@example.com",
            "--pack",
            "random-pics",
            "--note",
            "qa",
            "--no-refund",
        ]
    )
    assert revoke.no_refund is True
    assert revoke.refund is None


def test_grant_and_adjust_write_ledger(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"wallet-grant-{uuid.uuid4()}@example.com"
    )
    user = _user_from_token(db, auth_client, token)

    wallet, grant = grant_tokens(db, user_id=user.id, amount=100, note="welcome")
    assert wallet.balance == 100
    assert grant.kind == WalletLedgerKind.GRANT.value
    assert grant.delta == 100
    assert grant.balance_after == 100
    assert grant.note == "welcome"

    wallet, adjustment = adjust_tokens(db, user_id=user.id, delta=-30, note="correction")
    assert wallet.balance == 70
    assert adjustment.kind == WalletLedgerKind.ADJUSTMENT.value
    assert adjustment.delta == -30
    assert ledger_total(db, user_id=user.id) == 70

    by_kind = {entry.kind: entry.delta for entry in list_ledger(db, user_id=user.id)}
    assert by_kind == {
        WalletLedgerKind.GRANT.value: 100,
        WalletLedgerKind.ADJUSTMENT.value: -30,
    }


def test_reconcile_records_manual_db_balance(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"wallet-recon-{uuid.uuid4()}@example.com"
    )
    user = _user_from_token(db, auth_client, token)
    wallet = get_or_create_wallet(db, user_id=user.id)
    wallet.balance = 500
    db.flush()

    assert ledger_total(db, user_id=user.id) == 0
    wallet, entry = reconcile_wallet_ledger(db, user_id=user.id, note="manual DB grant 500")
    assert wallet.balance == 500
    assert entry is not None
    assert entry.kind == WalletLedgerKind.ADJUSTMENT.value
    assert entry.delta == 500
    assert entry.balance_after == 500
    assert entry.note == "manual DB grant 500"
    assert ledger_total(db, user_id=user.id) == 500

    again, noop = reconcile_wallet_ledger(db, user_id=user.id, note="already synced")
    assert again.balance == 500
    assert noop is None


def test_revoke_pack_refunds_original_charge(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"wallet-buyer-{uuid.uuid4()}@example.com"
    )
    buyer = _user_from_token(db, auth_client, token)
    paid = _published_pack(db, price=40)
    grant_tokens(db, user_id=buyer.id, amount=100, note="test float")
    unlock_pack(db, user=buyer, pack_id=paid.id)
    db.flush()
    assert get_or_create_wallet(db, user_id=buyer.id).balance == 60

    pack, refund, amount = revoke_pack_unlock(db, user=buyer, pack_id=paid.id, note="qa revoke")
    assert pack.id == paid.id
    assert amount == 40
    assert refund is not None
    assert refund.kind == WalletLedgerKind.REFUND.value
    assert refund.delta == 40
    assert refund.pack_id == paid.id
    assert refund.note == "qa revoke"
    assert get_or_create_wallet(db, user_id=buyer.id).balance == 100
    still_unlocked = db.scalar(
        select(IconPackUnlock.id).where(
            IconPackUnlock.user_id == buyer.id,
            IconPackUnlock.pack_id == paid.id,
        )
    )
    assert still_unlocked is None


def test_revoke_without_refund_keeps_tokens(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"wallet-buyer2-{uuid.uuid4()}@example.com"
    )
    buyer = _user_from_token(db, auth_client, token)
    paid = _published_pack(db, price=25)
    grant_tokens(db, user_id=buyer.id, amount=25, note="buy")
    unlock_pack(db, user=buyer, pack_id=paid.id)

    pack, refund, amount = revoke_pack_unlock(
        db, user=buyer, pack_id=paid.id, note="lock only", refund_amount=0
    )
    assert pack.id == paid.id
    assert amount == 0
    assert refund is None
    assert get_or_create_wallet(db, user_id=buyer.id).balance == 0

    with pytest.raises(MarketplaceError) as exc:
        revoke_pack_unlock(db, user=buyer, pack_id=paid.id, note="again")
    assert exc.value.code == ErrorCode.ICON_PACK_NOT_UNLOCKED


def test_adjust_cannot_go_negative(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"wallet-neg-{uuid.uuid4()}@example.com")
    user = _user_from_token(db, auth_client, token)
    grant_tokens(db, user_id=user.id, amount=10, note="small")
    with pytest.raises(WalletError) as exc:
        adjust_tokens(db, user_id=user.id, delta=-11, note="too much")
    assert exc.value.code == ErrorCode.INSUFFICIENT_TOKENS
    assert get_or_create_wallet(db, user_id=user.id).balance == 10
