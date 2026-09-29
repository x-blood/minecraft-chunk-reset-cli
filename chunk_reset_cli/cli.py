from __future__ import annotations

import argparse
import json
import os
import sys

from chunk_reset_cli.area import ResetArea, normalize_dimension_name
from chunk_reset_cli.pins import (
    DimensionPins,
    PinFileError,
    PinRect,
    list_pin_files,
    load_dimension_pins,
    pin_file_name,
    save_dimension_pins,
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
            "  chunk-reset pin add|remove|list PINDIR      manage pinned (protected) chunks\n"
            "  chunk-reset reset-all WORLD --pins PINDIR  delete everything except pinned chunks"
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
        "--pins",
        metavar="DIR",
        help=(
            "Directory with pin_<dimension>.json files: pinned chunks of the "
            "target dimension inside the area are NOT deleted"
        ),
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

    pins = None
    if args.pins:
        try:
            pins = load_dimension_pins(args.pins, args.dimension)
        except PinFileError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

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
            pins=pins,
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
            "Manage pinned chunks (chunks that reset-all will never delete). "
            "Pins are stored in a directory, one file per dimension: "
            "pin_overworld.json, pin_nether.json, pin_end.json. "
            "These commands never open or modify a world."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)

    add = sub.add_parser(
        "add", help="Pin an area (creates the directory / file if missing)"
    )
    add.add_argument("dir", help="Directory holding the pin files")
    _add_area_args(add, required=True)
    add.add_argument("--dimension", "-d", default="overworld")
    add.add_argument("--label", help="Optional name, unique per dimension")

    remove = sub.add_parser("remove", help="Remove a pin by label or by exact area")
    remove.add_argument("dir", help="Directory holding the pin files")
    remove.add_argument("--label", help="Label of the pin to remove")
    _add_area_args(remove, required=False)
    remove.add_argument("--dimension", "-d", default="overworld")

    lst = sub.add_parser("list", help="Show pinned areas (chunk coordinates)")
    lst.add_argument("dir", help="Directory holding the pin files")
    lst.add_argument(
        "--dimension", "-d", help="Show only this dimension (default: all pin files)"
    )
    return parser


def _pin_main(argv: list[str]) -> int:
    parser = build_pin_parser()
    args = parser.parse_args(argv)

    try:
        if args.action == "add":
            dimension = normalize_dimension_name(args.dimension)
            if os.path.isfile(args.dir):
                raise PinFileError(f"Not a directory: {args.dir}")
            created = not os.path.exists(os.path.join(args.dir, pin_file_name(dimension)))
            pins = (
                DimensionPins(dimension)
                if created
                else load_dimension_pins(args.dir, dimension)
            )
            rect = _pin_rect_from_args(args, args.label)
            pins.add(rect)
            path = save_dimension_pins(args.dir, pins)
            print(f"{'Created' if created else 'Updated'}: {path}")
            print(f"Pinned in {dimension}: {rect.describe()}")
            return 0

        if args.action == "remove":
            has_area = args.from_coord is not None or args.to_coord is not None
            if bool(args.label) == has_area:
                parser.error("specify either --label, or both --from and --to")
            if has_area and (args.from_coord is None or args.to_coord is None):
                parser.error("--from and --to must be given together")
            pins = load_dimension_pins(args.dir, args.dimension)
            if has_area:
                removed = pins.remove_by_area(_pin_rect_from_args(args))
            else:
                removed = pins.remove_by_label(args.label)
            save_dimension_pins(args.dir, pins)
            print(f"Removed from {pins.dimension}: {removed.describe()}")
            if not pins.rects:
                print(
                    f"Note: no pins remain for {pins.dimension}; "
                    "reset-all will refuse to run for it.",
                    file=sys.stderr,
                )
            return 0

        # list
        if args.dimension:
            names = [pin_file_name(args.dimension)]
            pin_sets = [load_dimension_pins(args.dir, args.dimension)]
        else:
            names = list_pin_files(args.dir)
            pin_sets = [_load_by_file_name(args.dir, name) for name in names]
        if not pin_sets:
            print("(no pin files)")
        for name, pins in zip(names, pin_sets):
            print(f"{pins.dimension}  ({name}):")
            if not pins.rects:
                print("  (no pins)")
            for rect in pins.rects:
                print(f"  {rect.describe()}")
        return 0
    except (PinFileError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _load_by_file_name(directory: str, name: str) -> DimensionPins:
    """Load a pin file found by naming convention, reading its dimension from the file."""
    path = os.path.join(directory, name)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PinFileError(f"Cannot read pin file {path}: {exc}") from exc
    dimension = data.get("dimension") if isinstance(data, dict) else None
    if not isinstance(dimension, str):
        raise PinFileError(f"{path}: 'dimension' must be a string.")
    pins = load_dimension_pins(directory, dimension)
    if pin_file_name(pins.dimension) != name:
        raise PinFileError(
            f"{path}: contains {pins.dimension} but the file name should be "
            f"{pin_file_name(pins.dimension)}."
        )
    return pins


# ---------------------------------------------------------------------------
# reset-all
# ---------------------------------------------------------------------------


def build_reset_all_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chunk-reset reset-all",
        description=(
            "Delete EVERY existing chunk in one dimension except the pinned chunks. "
            "Requires the pin file of that dimension (pin_<dimension>.json in the --pins directory) "
            "with at least one pin, "
            "and at least one pinned chunk that exists in the world. "
            "Back up your world and close Minecraft before running."
        ),
    )
    parser.add_argument("world", help="Path to the world folder (directory with level.dat)")
    parser.add_argument(
        "--pins",
        required=True,
        metavar="DIR",
        help=(
            "Directory with pin_<dimension>.json files "
            "(the file for --dimension is used; see 'chunk-reset pin --help')"
        ),
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
        pins = load_dimension_pins(args.pins, args.dimension)
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
