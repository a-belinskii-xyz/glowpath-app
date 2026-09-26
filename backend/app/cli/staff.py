"""CLI: grant or revoke the staff role.

Staff can grant tokens, author official icon packs, and export/import catalog
presets in the web console at ``/staff``.

Usage (from backend/ with venv, or ``make staff STAFF_ARGS='…'``)::

    python -m app.cli.staff list
    python -m app.cli.staff grant --user you@example.com
    python -m app.cli.staff revoke --user you@example.com
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli.wallet import resolve_user
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models.user import User
from app.services.staff_service import set_user_staff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli.staff")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="Print staff users")
    for name, help_text in (("grant", "Make a user staff"), ("revoke", "Remove staff role")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--user", required=True, help="Email or user UUID")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db: Session = SessionLocal()
    try:
        if args.command == "list":
            for user in db.scalars(select(User).where(User.is_staff.is_(True))).all():
                print(f"{user.id}  {user.email or '(telegram only)'}")
            return 0
        user = resolve_user(db, args.user)
        set_user_staff(db, user=user, is_staff=args.command == "grant")
        db.commit()
        print(f"{user.email or user.id}: is_staff={user.is_staff}")
        return 0
    except AppError as exc:
        db.rollback()
        print(exc.message, file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
