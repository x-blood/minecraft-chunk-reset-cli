"""Pinned (protected) chunk definitions stored in a JSON file.

The file is independent of any world. Pins are rectangles in chunk
coordinates, grouped by dimension::

    {
      "version": 1,
      "dimensions": {
        "minecraft:overworld": [
          {"from": [-22, 46], "to": [-20, 48], "label": "base"}
        ]
      }
    }
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from chunk_reset_cli.area import normalize_dimension_name

PIN_FILE_VERSION = 1


class PinFileError(ValueError):
    """The pin file is missing, unreadable, or has an invalid structure."""


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

    def same_area(self, other: "PinRect") -> bool:
        return self.bounds() == other.bounds()

    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.min_cx, self.min_cz, self.max_cx, self.max_cz)

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


class PinSet:
    def __init__(self, dimensions: Optional[Dict[str, List[PinRect]]] = None):
        self.dimensions: Dict[str, List[PinRect]] = dimensions or {}

    # -- queries -----------------------------------------------------------

    def rects(self, dimension: str) -> List[PinRect]:
        return list(self.dimensions.get(normalize_dimension_name(dimension), []))

    def total_rects(self) -> int:
        return sum(len(rects) for rects in self.dimensions.values())

    def contains(self, dimension: str, cx: int, cz: int) -> bool:
        return any(
            rect.contains(cx, cz)
            for rect in self.dimensions.get(normalize_dimension_name(dimension), [])
        )

    def has_label(self, label: str) -> bool:
        return any(
            rect.label == label
            for rects in self.dimensions.values()
            for rect in rects
        )

    # -- mutations ---------------------------------------------------------

    def add(self, dimension: str, rect: PinRect) -> None:
        dim = normalize_dimension_name(dimension)
        rects = self.dimensions.setdefault(dim, [])
        for existing in rects:
            if existing.same_area(rect):
                raise PinFileError(
                    f"The same area is already pinned in {dim}: {existing.describe()}"
                )
        if rect.label and self.has_label(rect.label):
            raise PinFileError(f"Label {rect.label!r} is already used.")
        rects.append(rect)

    def remove_by_label(self, label: str) -> Tuple[str, PinRect]:
        for dim, rects in self.dimensions.items():
            for rect in rects:
                if rect.label == label:
                    rects.remove(rect)
                    self._prune_empty()
                    return dim, rect
        raise PinFileError(f"No pin with label {label!r}.")

    def remove_by_area(self, dimension: str, target: PinRect) -> PinRect:
        dim = normalize_dimension_name(dimension)
        for rect in self.dimensions.get(dim, []):
            if rect.same_area(target):
                self.dimensions[dim].remove(rect)
                self._prune_empty()
                return rect
        raise PinFileError(
            f"No pin with exactly this area in {dim}. "
            "Use 'pin list' to see the registered areas (chunk coordinates)."
        )

    def _prune_empty(self) -> None:
        for dim in [d for d, rects in self.dimensions.items() if not rects]:
            del self.dimensions[dim]

    # -- (de)serialization -------------------------------------------------

    def to_json(self) -> Dict[str, Any]:
        return {
            "version": PIN_FILE_VERSION,
            "dimensions": {
                dim: [rect.to_json() for rect in rects]
                for dim, rects in sorted(self.dimensions.items())
            },
        }

    @classmethod
    def from_json(cls, data: Any) -> "PinSet":
        if not isinstance(data, dict):
            raise PinFileError("Top level must be a JSON object.")
        if data.get("version") != PIN_FILE_VERSION:
            raise PinFileError(
                f"Unsupported or missing 'version' (expected {PIN_FILE_VERSION})."
            )
        dims = data.get("dimensions")
        if not isinstance(dims, dict):
            raise PinFileError("'dimensions' must be an object.")

        pins = cls()
        for dim_name, entries in dims.items():
            if not isinstance(entries, list):
                raise PinFileError(f"dimensions[{dim_name!r}] must be a list.")
            for index, entry in enumerate(entries):
                where = f"dimensions[{dim_name!r}][{index}]"
                if not isinstance(entry, dict):
                    raise PinFileError(f"{where} must be an object.")
                corner_a = _parse_pair(entry.get("from"), f"{where}.from")
                corner_b = _parse_pair(entry.get("to"), f"{where}.to")
                label = entry.get("label")
                if label is not None and not isinstance(label, str):
                    raise PinFileError(f"{where}.label must be a string.")
                pins.add(dim_name, PinRect.from_corners(corner_a, corner_b, label or None))
        return pins


def _parse_pair(value: Any, where: str) -> Tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    ):
        raise PinFileError(f"{where} must be [X, Z] with integers.")
    return value[0], value[1]


def _format_pins(pins: PinSet) -> str:
    """Pretty-print with one line per pin so the file stays easy to hand-edit."""
    dumps = lambda value: json.dumps(value, ensure_ascii=False)  # noqa: E731
    lines = ["{", f'  "version": {PIN_FILE_VERSION},']
    if not pins.dimensions:
        lines.append('  "dimensions": {}')
    else:
        lines.append('  "dimensions": {')
        dims = sorted(pins.dimensions.items())
        for d_index, (dim, rects) in enumerate(dims):
            lines.append(f"    {dumps(dim)}: [")
            for r_index, rect in enumerate(rects):
                comma = "," if r_index < len(rects) - 1 else ""
                lines.append(f"      {dumps(rect.to_json())}{comma}")
            lines.append("    ]" + ("," if d_index < len(dims) - 1 else ""))
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def load_pins(path: str) -> PinSet:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise PinFileError(f"Pin file not found: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise PinFileError(f"Cannot read pin file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PinFileError(f"Invalid JSON in {path}: {exc}") from exc
    try:
        return PinSet.from_json(data)
    except PinFileError as exc:
        raise PinFileError(f"{path}: {exc}") from exc


def save_pins(path: str, pins: PinSet) -> None:
    """Write atomically so a crash never leaves a half-written pin file."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".pins-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_format_pins(pins))
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
