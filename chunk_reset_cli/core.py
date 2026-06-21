from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Tuple

from amulet.api.data_types import Dimension
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.level.load import load_level
from amulet.operations.delete_chunk import delete_chunk

CHUNK_SIZE = 16

DIMENSION_ALIASES = {
    "overworld": "minecraft:overworld",
    "nether": "minecraft:the_nether",
    "the_nether": "minecraft:the_nether",
    "end": "minecraft:the_end",
    "the_end": "minecraft:the_end",
}


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


def resolve_dimension(name: str, available: Iterable[Dimension]) -> Dimension:
    normalized = DIMENSION_ALIASES.get(name.lower(), name)
    dimensions = list(available)
    if normalized in dimensions:
        return normalized
    if name in dimensions:
        return name
    aliases = ", ".join(sorted(DIMENSION_ALIASES))
    available_text = ", ".join(dimensions) if dimensions else "(none)"
    raise ValueError(
        f"Unknown dimension {name!r}. "
        f"Available: {available_text}. Aliases: {aliases}."
    )


def build_selection(world, dimension: Dimension, area: ResetArea) -> SelectionGroup:
    bounds = world.bounds(dimension)
    return SelectionGroup(
        SelectionBox(
            (area.min_x, bounds.min[1], area.min_z),
            (area.max_x, bounds.max[1], area.max_z),
        )
    )


def reset_chunks_in_area(
    world_path: str,
    dimension: Dimension,
    area: ResetArea,
    *,
    dry_run: bool = False,
) -> Iterator[str]:
    world = load_level(world_path)
    world.open()
    try:
        selection = build_selection(world, dimension, area)
        chunks = [
            (cx, cz)
            for cx, cz in selection.chunk_locations()
            if world.has_chunk(cx, cz, dimension)
        ]
        yield f"World: {world_path}"
        yield f"Dimension: {dimension}"
        yield (
            f"Area (block coords): x={area.min_x}..{area.max_x - 1}, "
            f"z={area.min_z}..{area.max_z - 1}"
        )
        yield f"Chunks in selection: {len(list(selection.chunk_locations()))}"
        yield f"Chunks to delete (exist): {len(chunks)}"

        if dry_run:
            for cx, cz in sorted(chunks):
                yield f"  chunk ({cx}, {cz})"
            return

        if not chunks:
            yield "No chunks to delete."
            return

        for progress in delete_chunk(world, dimension, selection, load_original=False):
            if progress is not None:
                yield f"Deleting... {progress * 100:.0f}%"

        yield "Saving world..."
        for chunk_index, chunk_count in world.save_iter():
            if chunk_count:
                yield f"Saving... {chunk_index / chunk_count * 100:.0f}%"

        yield "Done."
    finally:
        world.close()
