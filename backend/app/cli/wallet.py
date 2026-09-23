"""CLI: audited token wallet and pack unlocks.

Every balance change writes ``wallet_ledger``. Do not UPDATE ``user_wallets``
by hand — use these commands so history explains every token.

Usage (from backend/ with venv, or ``make wallet WALLET_ARGS='…'``)::

    python -m app.cli.wallet show --user you@example.com
    python -m app.cli.wallet grant --user you@example.com --amount 500 --note "beta"
    python -m app.cli.wallet adjust --user you@example.com --delta -20 --note "typo"
    python -m app.cli.wallet reconcile --user you@example.com --note "manual DB +500"
    python -m app.cli.wallet ledger --user you@example.com
    python -m app.cli.wallet unlocks --user you@example.com
    python -m app.cli.wallet revoke --user you@example.com --pack random-pics --note "test"
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models.user import User
from app.models.wallet_ledger import WalletLedger
from app.services.auth_service import normalize_email
from app.services.marketplace_service import (
    get_pack_by_ref,
    list_user_unlocks,
    revoke_pack_unlock,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.wallet",
        description=(
            "Grant, adjust, or refund tokens with wallet_ledger rows. "
            "Use reconcile to explain a balance that was changed in the DB."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Print balance, ledger sum, and unlocks")
    _add_user_arg(show)

    grant = sub.add_parser("grant", help="Add tokens (kind=grant)")
    _add_user_arg(grant)
    grant.add_argument("--amount", type=int, required=True, help="Positive token amount")
    _add_note_arg(grant)
    _add_by_arg(grant)

    adjust = sub.add_parser("adjust", help="Signed correction (kind=adjustment)")
    _add_user_arg(adjust)
    adjust.add_argument(
        "--delta",
        type=int,
        required=True,
        help="Signed amount, e.g. 50 or -20 (balance cannot go below 0)",
    )
    _add_note_arg(adjust)
    _add_by_arg(adjust)

    reconcile = sub.add_parser(
        "reconcile",
        help="Write a ledger row for a balance already changed outside this CLI",
    )
    _add_user_arg(reconcile)
    _add_note_arg(reconcile)
    _add_by_arg(reconcile)

    ledger = sub.add_parser("ledger", help="Print recent wallet_ledger rows")
    _add_user_arg(ledger)
    ledger.add_argument("--limit", type=int, default=50, help="Max rows (default: 50)")

    unlocks = sub.add_parser("unlocks", help="List packs this user has unlocked")
    _add_user_arg(unlocks)

    revoke = sub.add_parser(
        "revoke",
        help="Remove a pack unlock and refund the original charge (kind=refund)",
    )
    _add_user_arg(revoke)
    revoke.add_argument(
        "--pack",
        required=True,
        help="Pack slug or UUID",
    )
    _add_note_arg(revoke)
    _add_by_arg(revoke)
    refund = revoke.add_mutually_exclusive_group()
    refund.add_argument(
        "--refund",
        type=int,
        metavar="AMOUNT",
        help="Override refund amount (default: what they paid to unlock)",
    )
    refund.add_argument(
        "--no-refund",
        action="store_true",
        help="Lock the pack without returning tokens",
    )
    return parser


def _add_user_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--user",
        required=True,
        help="User email or UUID",
    )


def _add_by_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--by",
        metavar="USER",
        help="Staff email or user UUID recorded as ledger created_by",
    )


def _add_note_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--note",
        required=True,
        help="Stored on wallet_ledger so the change is auditable",
    )


def _require_note(args: argparse.Namespace) -> str:
    note = str(args.note).strip()
    if not note:
        raise WalletError(
            "Note is required so the ledger explains this change",
            code=ErrorCode.WALLET_GRANT_INVALID,
        )
    return note


def resolve_user(db: Session, identifier: str) -> User:
    raw = identifier.strip()
    try:
        user_id = uuid.UUID(raw)
    except ValueError:
        user = db.scalar(select(User).where(User.email == normalize_email(raw)))
    else:
        user = db.get(User, user_id)
        if user is None:
            user = db.scalar(select(User).where(User.email == normalize_email(raw)))
    if user is None:
        raise WalletError(
            f"User not found: {identifier}",
            code=ErrorCode.USER_NOT_FOUND,
            status_code=404,
        )
    return user


def _format_entry(entry: WalletLedger) -> str:
    sign = "+" if entry.delta > 0 else ""
    pack = f" pack={entry.pack_id}" if entry.pack_id else ""
    note = f" note={entry.note!r}" if entry.note else ""
    when = entry.created_at.isoformat() if entry.created_at else ""
    return (
        f"{when}  {entry.kind:12} {sign}{entry.delta:<6} balance={entry.balance_after}{pack}{note}"
    )


def _print_wallet(db: Session, user: User) -> None:
    wallet = get_or_create_wallet(db, user_id=user.id)
    total = ledger_total(db, user_id=user.id)
    gap = wallet.balance - total
    print(f"User:    {user.email}  ({user.id})")
    print(f"Balance: {wallet.balance}")
    print(f"Ledger:  {total}  (sum of wallet_ledger.delta)")
    if gap:
        print(f"Gap:     {gap}  ← run reconcile --note '…' to record this in history")
    else:
        print("Gap:     0")


def cmd_show(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    _print_wallet(db, user)
    unlocks = list_user_unlocks(db, user_id=user.id)
    print()
    if not unlocks:
        print("Unlocks: none")
        return 0
    print("Unlocks:")
    for unlock in unlocks:
        pack = unlock.pack
        slug = pack.slug if pack is not None else str(unlock.pack_id)
        price = pack.price_tokens if pack is not None else "?"
        print(f"  {slug}  price={price}  unlocked_at={unlock.unlocked_at.isoformat()}")
    return 0


def cmd_grant(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    actor = resolve_user(db, args.by) if args.by else None
    wallet, entry = grant_tokens(
        db,
        user_id=user.id,
        amount=args.amount,
        note=_require_note(args),
        created_by=actor.id if actor else None,
    )
    print(f"Granted {args.amount} tokens to {user.email}")
    print(f"Balance: {wallet.balance}")
    print(_format_entry(entry))
    return 0


def cmd_adjust(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    actor = resolve_user(db, args.by) if args.by else None
    wallet, entry = adjust_tokens(
        db,
        user_id=user.id,
        delta=args.delta,
        note=_require_note(args),
        created_by=actor.id if actor else None,
    )
    print(f"Adjusted {user.email} by {args.delta}")
    print(f"Balance: {wallet.balance}")
    print(_format_entry(entry))
    return 0


def cmd_reconcile(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    actor = resolve_user(db, args.by) if args.by else None
    wallet, entry = reconcile_wallet_ledger(
        db,
        user_id=user.id,
        note=_require_note(args),
        created_by=actor.id if actor else None,
    )
    if entry is None:
        print(f"{user.email}: already in sync (balance={wallet.balance})")
        return 0
    print(f"Recorded gap of {entry.delta} for {user.email} without changing balance")
    print(f"Balance: {wallet.balance}")
    print(_format_entry(entry))
    return 0


def cmd_ledger(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    _print_wallet(db, user)
    print()
    entries = list_ledger(db, user_id=user.id, limit=max(1, args.limit))
    if not entries:
        print("No wallet_ledger rows")
        return 0
    for entry in entries:
        print(_format_entry(entry))
    return 0


def cmd_unlocks(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    unlocks = list_user_unlocks(db, user_id=user.id)
    if not unlocks:
        print(f"{user.email}: no unlocked packs")
        return 0
    print(f"{user.email}: {len(unlocks)} unlocked pack(s)")
    for unlock in unlocks:
        pack = unlock.pack
        slug = pack.slug if pack is not None else str(unlock.pack_id)
        price = pack.price_tokens if pack is not None else "?"
        print(f"  {slug}  id={unlock.pack_id}  price={price}  at={unlock.unlocked_at.isoformat()}")
    return 0


def cmd_revoke(db: Session, args: argparse.Namespace) -> int:
    user = resolve_user(db, args.user)
    actor = resolve_user(db, args.by) if args.by else None
    pack = get_pack_by_ref(db, args.pack)
    refund_amount: int | None
    if args.no_refund:
        refund_amount = 0
    elif args.refund is not None:
        refund_amount = args.refund
    else:
        refund_amount = None
    _pack, entry, refunded = revoke_pack_unlock(
        db,
        user=user,
        pack_id=pack.id,
        note=_require_note(args),
        created_by=actor.id if actor else None,
        refund_amount=refund_amount,
    )
    print(f"Revoked {pack.slug} from {user.email}")
    if refunded == 0:
        print("No tokens refunded")
    elif entry is not None:
        print(f"Refunded {refunded} tokens")
        print(_format_entry(entry))
    wallet = get_or_create_wallet(db, user_id=user.id)
    print(f"Balance: {wallet.balance}")
    return 0


_COMMANDS: dict[str, Callable[[Session, argparse.Namespace], int]] = {
    "show": cmd_show,
    "grant": cmd_grant,
    "adjust": cmd_adjust,
    "reconcile": cmd_reconcile,
    "ledger": cmd_ledger,
    "unlocks": cmd_unlocks,
    "revoke": cmd_revoke,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = _COMMANDS[args.command]
    db = SessionLocal()
    try:
        code = handler(db, args)
        db.commit()
        return code
    except AppError as exc:
        db.rollback()
        print(exc.message, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        db.rollback()
        print(f"Wallet command failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
