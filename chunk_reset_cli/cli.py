from __future__ import annotations

import argparse
import sys

from chunk_reset_cli.core import ResetArea, reset_chunks_in_area, resolve_dimension


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


def main(argv: list[str] | None = None) -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
