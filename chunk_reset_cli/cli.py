from __future__ import annotations

import argparse
import os
import sys

from chunk_reset_cli.area import ResetArea, normalize_dimension_name
from chunk_reset_cli.pins import (
    PinFileError,
    PinRect,
    PinSet,
    load_pins,
    save_pins,
)


def _parse_coord(value: str) -> tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected X,Z (e.g. 100,200)")
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("coordinates must be integers") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chunk-reset",
        description=(
            "Delete Minecraft chunks in a rectangular area so they regenerate in-game. "
            "Back up your world and close Minecraft before running."
        ),
        epilog=(
            "Other commands (run with --help for details):\n"
            "  chunk-reset pin add|remove|list PINFILE   manage pinned (protected) chunks\n"
            "  chunk-reset reset-all WORLD --pins PINFILE  delete everything except pinned chunks"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "world",
        help="Path to the world folder (level.dat のあるディレクトリ)",
    )
    parser.add_argument(
        "--from",
        dest="from_coord",
        required=True,
        type=_parse_coord,
        metavar="X,Z",
        help="One corner of the area (block or chunk coords)",
    )
    parser.add_argument(
        "--to",
        dest="to_coord",
        required=True,
        type=_parse_coord,
        metavar="X,Z",
        help="Opposite corner of the area (block or chunk coords)",
    )
    parser.add_argument(
        "--dimension",
        "-d",
        default="overworld",
        help="Dimension: overworld, nether, end, or minecraft:overworld form (default: overworld)",
    )
    parser.add_argument(
        "--chunk-coords",
        action="store_true",
        help="Treat --from / --to as chunk coordinates instead of block coordinates",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List chunks that would be deleted without modifying the world",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return parser


def _reset_area_main(argv: list[str]) -> int:
    from chunk_reset_cli.core import reset_chunks_in_area

    parser = build_parser()
    args = parser.parse_args(argv)

    area = ResetArea.from_corners(
        args.from_coord,
        args.to_coord,
        chunk_coords=args.chunk_coords,
    )

    if not args.yes and not args.dry_run:
        coord_type = "chunk" if args.chunk_coords else "block"
        print(
            f"This will permanently delete up to {area.chunk_count()} chunk(s) "
            f"in {args.world!r} ({coord_type} area).",
            file=sys.stderr,
        )
        print("Make sure you have a backup and Minecraft is closed.", file=sys.stderr)
        try:
            answer = input("Continue? [y/N]: ").strip().lower()
        except EOFError:
            print("Cancelled.", file=sys.stderr)
            return 1
        if answer not in ("y", "yes"):
            print("Cancelled.", file=sys.stderr)
            return 1

    try:
        for line in reset_chunks_in_area(
            args.world,
            args.dimension,
            area,
            dry_run=args.dry_run,
        ):
            print(line)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


# ---------------------------------------------------------------------------
# pin subcommands
# ---------------------------------------------------------------------------


def _add_area_args(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument(
        "--from",
        dest="from_coord",
        required=required,
        type=_parse_coord,
        metavar="X,Z",
        help="One corner (block coords by default). For negatives use --from=-352,736",
    )
    parser.add_argument(
        "--to",
        dest="to_coord",
        required=required,
        type=_parse_coord,
        metavar="X,Z",
        help="Opposite corner. For negatives use --to=-100,800",
    )
    parser.add_argument(
        "--chunk-coords",
        action="store_true",
        help="Treat --from / --to as chunk coordinates instead of block coordinates",
    )


def _pin_rect_from_args(args: argparse.Namespace, label: str | None = None) -> PinRect:
    area = ResetArea.from_corners(
        args.from_coord, args.to_coord, chunk_coords=args.chunk_coords
    )
    min_cx, min_cz, max_cx, max_cz = area.chunk_rect()
    return PinRect(min_cx, min_cz, max_cx, max_cz, label)


def build_pin_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chunk-reset pin",
        description=(
            "Manage the JSON file that defines pinned chunks "
            "(chunks that reset-all will never delete). "
            "This does not open or modify any world."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)

    add = sub.add_parser("add", help="Pin an area (creates the file if missing)")
    add.add_argument("file", help="Path to the pin JSON file")
    _add_area_args(add, required=True)
    add.add_argument("--dimension", "-d", default="overworld")
    add.add_argument("--label", help="Optional unique name, usable with 'pin remove --label'")

    remove = sub.add_parser("remove", help="Remove a pin by label or by exact area")
    remove.add_argument("file", help="Path to the pin JSON file")
    remove.add_argument("--label", help="Label of the pin to remove")
    _add_area_args(remove, required=False)
    remove.add_argument("--dimension", "-d", default="overworld")

    lst = sub.add_parser("list", help="Show pinned areas (chunk coordinates)")
    lst.add_argument("file", help="Path to the pin JSON file")
    lst.add_argument("--dimension", "-d", help="Show only this dimension")
    return parser


def _pin_main(argv: list[str]) -> int:
    parser = build_pin_parser()
    args = parser.parse_args(argv)

    try:
        if args.action == "add":
            created = not os.path.exists(args.file)
            pins = PinSet() if created else load_pins(args.file)
            rect = _pin_rect_from_args(args, args.label)
            pins.add(args.dimension, rect)
            save_pins(args.file, pins)
            print(f"{'Created' if created else 'Updated'}: {args.file}")
            print(f"Pinned in {normalize_dimension_name(args.dimension)}: {rect.describe()}")
            return 0

        pins = load_pins(args.file)

        if args.action == "remove":
            has_area = args.from_coord is not None or args.to_coord is not None
            if bool(args.label) == has_area:
                parser.error("specify either --label, or both --from and --to")
            if has_area:
                if args.from_coord is None or args.to_coord is None:
                    parser.error("--from and --to must be given together")
                removed = pins.remove_by_area(args.dimension, _pin_rect_from_args(args))
                dim = normalize_dimension_name(args.dimension)
            else:
                dim, removed = pins.remove_by_label(args.label)
            save_pins(args.file, pins)
            print(f"Removed from {dim}: {removed.describe()}")
            if pins.total_rects() == 0:
                print(
                    "Note: no pins remain; reset-all will refuse to run with this file.",
                    file=sys.stderr,
                )
            return 0

        # list
        selected = (
            {normalize_dimension_name(args.dimension)} if args.dimension else None
        )
        shown = 0
        for dim, rects in sorted(pins.dimensions.items()):
            if selected is not None and dim not in selected:
                continue
            print(f"{dim}:")
            for rect in rects:
                print(f"  {rect.describe()}")
                shown += 1
        if shown == 0:
            print("(no pins)")
        return 0
    except PinFileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# reset-all
# ---------------------------------------------------------------------------


def build_reset_all_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chunk-reset reset-all",
        description=(
            "Delete EVERY existing chunk in one dimension except the pinned chunks. "
            "Requires a pin file with at least one pin in that dimension, "
            "and at least one pinned chunk that exists in the world. "
            "Back up your world and close Minecraft before running."
        ),
    )
    parser.add_argument("world", help="Path to the world folder (directory with level.dat)")
    parser.add_argument(
        "--pins",
        required=True,
        metavar="FILE",
        help="Pin JSON file (see 'chunk-reset pin --help')",
    )
    parser.add_argument(
        "--dimension",
        "-d",
        default="overworld",
        help="Dimension to reset (default: overworld). Other dimensions are untouched.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List chunks that would be deleted without modifying the world",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (safety checks still apply)",
    )
    return parser


def _reset_all_main(argv: list[str]) -> int:
    from chunk_reset_cli.core import PruneCancelled, reset_all_except_pins

    parser = build_reset_all_parser()
    args = parser.parse_args(argv)

    try:
        pins = load_pins(args.pins)
    except PinFileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    def confirm(plan) -> bool:
        if args.yes:
            return True
        print(
            f"\nThis will permanently delete {len(plan.delete)} chunk(s) in "
            f"{plan.dimension} and keep {len(plan.keep)} pinned chunk(s).",
            file=sys.stderr,
        )
        print("Make sure you have a backup and Minecraft is closed.", file=sys.stderr)
        try:
            answer = input("Continue? [y/N]: ").strip().lower()
        except EOFError:
            return False
        return answer in ("y", "yes")

    try:
        for line in reset_all_except_pins(
            args.world,
            args.dimension,
            pins,
            dry_run=args.dry_run,
            confirm=confirm,
        ):
            print(line)
    except PruneCancelled:
        print("Cancelled.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "pin":
        return _pin_main(argv[1:])
    if argv and argv[0] == "reset-all":
        return _reset_all_main(argv[1:])
    return _reset_area_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
