"""Pinned (protected) chunk definitions stored as JSON files.

Pins live in a *directory*, one file per dimension, named by convention:

    pin_overworld.json
    pin_nether.json
    pin_end.json

Each file holds rectangles in chunk coordinates for that dimension only::

    {
      "version": 1,
      "dimension": "minecraft:overworld",
      "pins": [
        {"from": [-22, 46], "to": [-20, 48], "label": "base"}
      ]
    }

The files are independent of any world.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from chunk_reset_cli.area import dimension_file_key, normalize_dimension_name

PIN_FILE_VERSION = 1
PIN_FILE_PREFIX = "pin_"
PIN_FILE_SUFFIX = ".json"


class PinFileError(ValueError):
    """A pin file / directory is missing, unreadable, or invalid."""


@dataclass(frozen=True)
class PinRect:
    """Inclusive rectangle in chunk coordinates."""

    min_cx: int
    min_cz: int
    max_cx: int
    max_cz: int
    label: Optional[str] = None

    @classmethod
    def from_corners(
        cls,
        corner_a: Tuple[int, int],
        corner_b: Tuple[int, int],
        label: Optional[str] = None,
    ) -> "PinRect":
        (x1, z1), (x2, z2) = corner_a, corner_b
        return cls(min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2), label)

    def contains(self, cx: int, cz: int) -> bool:
        return self.min_cx <= cx <= self.max_cx and self.min_cz <= cz <= self.max_cz

    def chunk_count(self) -> int:
        return (self.max_cx - self.min_cx + 1) * (self.max_cz - self.min_cz + 1)

    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.min_cx, self.min_cz, self.max_cx, self.max_cz)

    def same_area(self, other: "PinRect") -> bool:
        return self.bounds() == other.bounds()

    def describe(self) -> str:
        text = f"({self.min_cx}, {self.min_cz}) .. ({self.max_cx}, {self.max_cz})"
        text += f" [{self.chunk_count()} chunk(s)]"
        if self.label:
            text += f" label={self.label!r}"
        return text

    def to_json(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "from": [self.min_cx, self.min_cz],
            "to": [self.max_cx, self.max_cz],
        }
        if self.label:
            data["label"] = self.label
        return data


class DimensionPins:
    """The pins of a single dimension."""

    def __init__(self, dimension: str, rects: Optional[List[PinRect]] = None):
        self.dimension = normalize_dimension_name(dimension)
        self.rects: List[PinRect] = list(rects or [])

    def contains(self, cx: int, cz: int) -> bool:
        return any(rect.contains(cx, cz) for rect in self.rects)

    def add(self, rect: PinRect) -> None:
        for existing in self.rects:
            if existing.same_area(rect):
                raise PinFileError(
                    f"The same area is already pinned in {self.dimension}: "
                    f"{existing.describe()}"
                )
        if rect.label and any(r.label == rect.label for r in self.rects):
            raise PinFileError(
                f"Label {rect.label!r} is already used in {self.dimension}."
            )
        self.rects.append(rect)

    def remove_by_label(self, label: str) -> PinRect:
        for rect in self.rects:
            if rect.label == label:
                self.rects.remove(rect)
                return rect
        raise PinFileError(f"No pin with label {label!r} in {self.dimension}.")

    def remove_by_area(self, target: PinRect) -> PinRect:
        for rect in self.rects:
            if rect.same_area(target):
                self.rects.remove(rect)
                return rect
        raise PinFileError(
            f"No pin with exactly this area in {self.dimension}. "
            "Use 'pin list' to see the registered areas (chunk coordinates)."
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "version": PIN_FILE_VERSION,
            "dimension": self.dimension,
            "pins": [rect.to_json() for rect in self.rects],
        }

    @classmethod
    def from_json(cls, data: Any, expected_dimension: str) -> "DimensionPins":
        expected = normalize_dimension_name(expected_dimension)
        if not isinstance(data, dict):
            raise PinFileError("Top level must be a JSON object.")
        if data.get("version") != PIN_FILE_VERSION:
            raise PinFileError(
                f"Unsupported or missing 'version' (expected {PIN_FILE_VERSION})."
            )
        dimension = data.get("dimension")
        if not isinstance(dimension, str):
            raise PinFileError("'dimension' must be a string.")
        if normalize_dimension_name(dimension) != expected:
            raise PinFileError(
                f"'dimension' is {dimension!r} but this file is used for {expected}. "
                "Was the file renamed or copied from another dimension?"
            )
        entries = data.get("pins")
        if not isinstance(entries, list):
            raise PinFileError("'pins' must be a list.")

        pins = cls(expected)
        for index, entry in enumerate(entries):
            where = f"pins[{index}]"
            if not isinstance(entry, dict):
                raise PinFileError(f"{where} must be an object.")
            corner_a = _parse_pair(entry.get("from"), f"{where}.from")
            corner_b = _parse_pair(entry.get("to"), f"{where}.to")
            label = entry.get("label")
            if label is not None and not isinstance(label, str):
                raise PinFileError(f"{where}.label must be a string.")
            pins.add(PinRect.from_corners(corner_a, corner_b, label or None))
        return pins


def _parse_pair(value: Any, where: str) -> Tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    ):
        raise PinFileError(f"{where} must be [X, Z] with integers.")
    return value[0], value[1]


# -- files -------------------------------------------------------------------


def pin_file_name(dimension: str) -> str:
    return f"{PIN_FILE_PREFIX}{dimension_file_key(dimension)}{PIN_FILE_SUFFIX}"


def pin_file_path(directory: str, dimension: str) -> str:
    return os.path.join(directory, pin_file_name(dimension))


def _require_directory(directory: str) -> None:
    if os.path.isfile(directory):
        raise PinFileError(
            f"--pins / pin directory must be a directory, not a file: {directory}"
        )
    if not os.path.isdir(directory):
        raise PinFileError(f"Pin directory not found: {directory}")


def load_dimension_pins(directory: str, dimension: str) -> DimensionPins:
    """Load ``pin_<dimension>.json`` from ``directory``; error if it is missing."""
    _require_directory(directory)
    path = pin_file_path(directory, dimension)
    if not os.path.isfile(path):
        raise PinFileError(
            f"Pin file for {normalize_dimension_name(dimension)} not found: {path}"
        )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError) as exc:
        raise PinFileError(f"Cannot read pin file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PinFileError(f"Invalid JSON in {path}: {exc}") from exc
    try:
        return DimensionPins.from_json(data, dimension)
    except PinFileError as exc:
        raise PinFileError(f"{path}: {exc}") from exc


def save_dimension_pins(directory: str, pins: DimensionPins) -> str:
    """Write ``pin_<dimension>.json`` atomically (creates the directory). Returns the path."""
    os.makedirs(directory, exist_ok=True)
    path = pin_file_path(directory, pins.dimension)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".pins-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_format_pins(pins))
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return path


def list_pin_files(directory: str) -> List[str]:
    """Names of files in ``directory`` that follow the pin file naming convention."""
    _require_directory(directory)
    return sorted(
        name
        for name in os.listdir(directory)
        if name.startswith(PIN_FILE_PREFIX)
        and name.endswith(PIN_FILE_SUFFIX)
        and os.path.isfile(os.path.join(directory, name))
    )


def _format_pins(pins: DimensionPins) -> str:
    """One line per pin so the file stays easy to hand-edit."""
    dumps = lambda value: json.dumps(value, ensure_ascii=False)  # noqa: E731
    lines = [
        "{",
        f'  "version": {PIN_FILE_VERSION},',
        f'  "dimension": {dumps(pins.dimension)},',
    ]
    if not pins.rects:
        lines.append('  "pins": []')
    else:
        lines.append('  "pins": [')
        for index, rect in enumerate(pins.rects):
            comma = "," if index < len(pins.rects) - 1 else ""
            lines.append(f"    {dumps(rect.to_json())}{comma}")
        lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"
