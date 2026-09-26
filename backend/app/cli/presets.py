"""CLI: export / import catalog presets (icon packs + achievements).

A preset is a zip (or unpacked folder) in the seed format described in
``app/services/preset_service.py``. Import is idempotent: packs, icons and
achievements are upserted by slug.

Usage (from backend/ with venv, or ``make preset-export`` / ``make preset-import``)::

    python -m app.cli.presets export --out preset.zip
    python -m app.cli.presets export --out preset.zip --pack foxes --pack weather
    python -m app.cli.presets export --out packs.zip --no-achievements
    python -m app.cli.presets import preset.zip
    python -m app.cli.presets import ./unpacked-preset/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.services.marketplace_service import get_pack_by_ref
from app.services.preset_service import export_preset, import_preset_path
from app.services.storage import storage_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli.presets")
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="Write packs + achievements to a zip")
    export.add_argument("--out", required=True, type=Path, help="Target .zip path")
    export.add_argument(
        "--pack",
        action="append",
        default=None,
        help="Pack slug or id (repeatable). Default: every official pack",
    )
    export.add_argument("--no-achievements", action="store_true")

    load = sub.add_parser("import", help="Load a preset zip or folder")
    load.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = SessionLocal()
    try:
        if args.command == "export":
            pack_ids = (
                None if args.pack is None else [get_pack_by_ref(db, ref).id for ref in args.pack]
            )
            data, manifest = export_preset(
                db,
                storage=storage_service,
                pack_ids=pack_ids,
                include_achievements=not args.no_achievements,
            )
            args.out.write_bytes(data)
            print(
                f"Wrote {args.out}: packs={len(manifest['packs'])} icons={manifest['icons']} "
                f"achievements={len(manifest['achievements'])}"
            )
            return 0
        report = import_preset_path(db, storage=storage_service, path=args.path)
        db.commit()
        print(
            f"Imported search_tags={report.search_tags} packs={len(report.packs)} "
            f"icons={report.icons} achievements={len(report.achievements)}"
        )
        for slug in report.packs:
            print(f"  pack {slug}")
        return 0
    except AppError as exc:
        db.rollback()
        print(exc.message, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        db.rollback()
        print(f"Preset command failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
