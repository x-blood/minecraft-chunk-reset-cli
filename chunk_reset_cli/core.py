from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional

from amulet.api.chunk import Chunk
from amulet.api.data_types import Dimension
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.level.load import load_level
from amulet.operations.delete_chunk import delete_chunk

from chunk_reset_cli.area import (  # noqa: F401  (re-exported)
    CHUNK_SIZE,
    DIMENSION_ALIASES,
    ResetArea,
    normalize_dimension_name,
)
from chunk_reset_cli.pins import DimensionPins


def resolve_dimension(name: str, available: Iterable[Dimension]) -> Dimension:
    normalized = normalize_dimension_name(name)
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
    dimension_name: str,
    area: ResetArea,
    *,
    dry_run: bool = False,
    pins: Optional[DimensionPins] = None,
) -> Iterator[str]:
    """Delete existing chunks inside ``area``.

    If ``pins`` is given (pins of the target dimension), pinned chunks inside
    the area are skipped.
    """
    world = load_level(world_path)
    try:
        dimension = resolve_dimension(dimension_name, world.dimensions)
        selection = build_selection(world, dimension, area)
        chunks = [
            (cx, cz)
            for cx, cz in selection.chunk_locations()
            if world.has_chunk(cx, cz, dimension)
        ]
        skipped = []
        if pins is not None:
            if pins.dimension != dimension:
                raise ValueError(
                    f"Pins are for {pins.dimension} but the target is {dimension}."
                )
            skipped = [c for c in chunks if pins.contains(*c)]
            chunks = [c for c in chunks if not pins.contains(*c)]
        yield f"World: {world_path}"
        yield f"Dimension: {dimension}"
        yield (
            f"Area (block coords): x={area.min_x}..{area.max_x - 1}, "
            f"z={area.min_z}..{area.max_z - 1}"
        )
        yield f"Chunks in selection: {len(list(selection.chunk_locations()))}"
        if pins is not None:
            yield f"Chunks skipped (pinned, exist): {len(skipped)}"
        yield f"Chunks to delete (exist): {len(chunks)}"

        if dry_run:
            for cx, cz in sorted(chunks):
                yield f"  chunk ({cx}, {cz})"
            return

        if not chunks:
            yield "No chunks to delete."
            return

        if pins is None:
            for progress in delete_chunk(
                world, dimension, selection, load_original=False
            ):
                if progress is not None:
                    yield f"Deleting... {progress * 100:.0f}%"
        else:
            # Delete only the non-pinned chunks (same mechanism as above).
            for progress in _delete_chunks_fast(world, dimension, chunks):
                yield f"Deleting... {progress * 100:.0f}%"

        yield "Saving world..."
        for chunk_index, chunk_count in world.save_iter():
            if chunk_count:
                yield f"Saving... {chunk_index / chunk_count * 100:.0f}%"

        yield "Done."
    finally:
        world.close()


class PruneRefused(ValueError):
    """reset-all refused to run because a safety condition was not met."""


class PruneCancelled(Exception):
    """The user declined the confirmation prompt."""


@dataclass(frozen=True)
class PrunePlan:
    dimension: Dimension
    total: int
    keep: list
    delete: list


def _delete_chunks_fast(world, dimension: Dimension, chunks: list) -> Iterator[float]:
    """Delete chunks without loading each original chunk for undo history.

    Mirrors what Amulet's own ``delete_chunk`` operation does with
    ``load_original=False`` (registers an empty placeholder as the original).
    """
    count = len(chunks)
    for index, (cx, cz) in enumerate(chunks, start=1):
        world.delete_chunk(cx, cz, dimension)
        key = (dimension, cx, cz)
        if key not in world.chunks._history_database:
            world.chunks._register_original_entry(key, Chunk(cx, cz))
        yield index / count


def reset_all_except_pins(
    world_path: str,
    dimension_name: str,
    pins: DimensionPins,
    *,
    dry_run: bool = False,
    confirm: Optional[Callable[[PrunePlan], bool]] = None,
) -> Iterator[str]:
    """Delete every existing chunk in a dimension except the pinned ones.

    Safety guards (all raise :class:`PruneRefused`, nothing is modified):

    * the pin file for the target dimension must define at least one pin;
    * at least one pinned chunk must actually exist in the world, so a
      wrong dimension or mistyped coordinates can never wipe everything.
    """
    normalized = normalize_dimension_name(dimension_name)
    if pins.dimension != normalized:
        raise PruneRefused(
            f"Pins are for {pins.dimension} but the target is {normalized}."
        )
    pin_rects = pins.rects
    if not pin_rects:
        raise PruneRefused(
            f"No pinned chunks are defined for {normalized} in the pin file. "
            "Refusing to delete all chunks. Add pins with 'chunk-reset pin add'."
        )

    world = load_level(world_path)
    try:
        dimension = resolve_dimension(dimension_name, world.dimensions)
        all_chunks = set(world.all_chunk_coords(dimension))
        keep = sorted(c for c in all_chunks if pins.contains(*c))
        if not keep:
            raise PruneRefused(
                f"None of the {len(pin_rects)} pinned area(s) contain an existing "
                f"chunk in {dimension}. Refusing to delete all chunks. "
                "Check the dimension and pin coordinates."
            )
        delete = sorted(all_chunks - set(keep))
        plan = PrunePlan(dimension, len(all_chunks), keep, delete)

        yield f"World: {world_path}"
        yield f"Dimension: {dimension}"
        yield f"Pinned areas: {len(pin_rects)}"
        yield f"Existing chunks: {plan.total}"
        yield f"Chunks kept (pinned, exist): {len(keep)}"
        yield f"Chunks to delete: {len(delete)}"

        if dry_run:
            for cx, cz in delete:
                yield f"  chunk ({cx}, {cz})"
            return

        if not delete:
            yield "No chunks to delete."
            return

        if confirm is not None and not confirm(plan):
            raise PruneCancelled()

        last_pct = -1
        for progress in _delete_chunks_fast(world, dimension, delete):
            pct = int(progress * 100)
            if pct >= last_pct + 10 or pct == 100:
                last_pct = pct
                yield f"Deleting... {pct}%"

        yield "Saving world..."
        last_pct = -1
        for chunk_index, chunk_count in world.save_iter():
            if chunk_count:
                pct = int(chunk_index / chunk_count * 100)
                if pct >= last_pct + 10 or pct == 100:
                    last_pct = pct
                    yield f"Saving... {pct}%"

        yield "Done."
    finally:
        world.close()
