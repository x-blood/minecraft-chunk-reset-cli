"""Pure helpers (no Amulet dependency): coordinates, areas, dimension names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

CHUNK_SIZE = 16

DIMENSION_ALIASES = {
    "overworld": "minecraft:overworld",
    "nether": "minecraft:the_nether",
    "the_nether": "minecraft:the_nether",
    "end": "minecraft:the_end",
    "the_end": "minecraft:the_end",
}


def normalize_dimension_name(name: str) -> str:
    """Map an alias such as ``nether`` to ``minecraft:the_nether``."""
    return DIMENSION_ALIASES.get(name.lower(), name)


@dataclass(frozen=True)
class ResetArea:
    min_x: int
    min_z: int
    max_x: int
    max_z: int
    chunk_coords: bool

    @classmethod
    def from_corners(
        cls,
        corner_a: Tuple[int, int],
        corner_b: Tuple[int, int],
        *,
        chunk_coords: bool,
    ) -> "ResetArea":
        x1, z1 = corner_a
        x2, z2 = corner_b

        if chunk_coords:
            min_cx, max_cx = sorted((x1, x2))
            min_cz, max_cz = sorted((z1, z2))
            return cls(
                min_x=min_cx * CHUNK_SIZE,
                min_z=min_cz * CHUNK_SIZE,
                max_x=(max_cx + 1) * CHUNK_SIZE,
                max_z=(max_cz + 1) * CHUNK_SIZE,
                chunk_coords=True,
            )

        min_x, max_x = sorted((x1, x2))
        min_z, max_z = sorted((z1, z2))
        return cls(
            min_x=(min_x // CHUNK_SIZE) * CHUNK_SIZE,
            min_z=(min_z // CHUNK_SIZE) * CHUNK_SIZE,
            max_x=((max_x // CHUNK_SIZE) + 1) * CHUNK_SIZE,
            max_z=((max_z // CHUNK_SIZE) + 1) * CHUNK_SIZE,
            chunk_coords=False,
        )

    def chunk_count(self) -> int:
        width = (self.max_x - self.min_x) // CHUNK_SIZE
        depth = (self.max_z - self.min_z) // CHUNK_SIZE
        return width * depth

    def chunk_rect(self) -> Tuple[int, int, int, int]:
        """Inclusive chunk bounds: (min_cx, min_cz, max_cx, max_cz)."""
        return (
            self.min_x // CHUNK_SIZE,
            self.min_z // CHUNK_SIZE,
            self.max_x // CHUNK_SIZE - 1,
            self.max_z // CHUNK_SIZE - 1,
        )

    def chunk_coords_list(self) -> list[Tuple[int, int]]:
        min_cx = self.min_x // CHUNK_SIZE
        max_cx = self.max_x // CHUNK_SIZE
        min_cz = self.min_z // CHUNK_SIZE
        max_cz = self.max_z // CHUNK_SIZE
        return [
            (cx, cz)
            for cx in range(min_cx, max_cx)
            for cz in range(min_cz, max_cz)
        ]
