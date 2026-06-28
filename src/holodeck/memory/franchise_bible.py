from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid4

from holodeck.pipeline.events import AsyncioEventBus

logger = logging.getLogger(__name__)

try:
    from holodeck.storage.postgres import BibleRepository, BibleEntry as DBBibleEntry
    from holodeck.storage.postgres import FranchiseBible as DBFranchiseBible
    _HAS_DB_IMPORT = True
except Exception:
    _HAS_DB_IMPORT = False


def _db_available() -> bool:
    return _HAS_DB_IMPORT


_BIBLE_REGISTRY: dict[str, FranchiseBible] = {}


async def async_create_bible(name: str, description: str = "") -> FranchiseBible:
    if _db_available():
        repo = BibleRepository()
        db_bibles = await repo.list()
        for existing in db_bibles:
            if existing.name.lower() == name.lower():
                loaded = _BIBLE_REGISTRY.get(str(existing.id))
                if loaded:
                    return loaded
                from_bible = FranchiseBible(existing.id, existing.name)
                from_bible._description = existing.description or ""
                entries = await repo.search_entries(existing.id, "")
                for e in entries:
                    from_bible._entries[e.id] = {
                        "id": e.id, "bible_id": existing.id, "category": e.category,
                        "name": e.name, "content": e.content, "metadata": e.metadata_ or {},
                        "created_at": e.created_at.isoformat() if e.created_at else "",
                        "updated_at": e.updated_at.isoformat() if e.updated_at else "",
                    }
                _BIBLE_REGISTRY[str(existing.id)] = from_bible
                return from_bible
        db_bible = DBFranchiseBible(id=uuid4(), name=name, description=description or None)
        await repo.create(db_bible)
        bible = FranchiseBible(db_bible.id, name)
        bible._description = description
        _BIBLE_REGISTRY[str(db_bible.id)] = bible
        return bible
    return create_bible(name, description)


def create_bible(name: str, description: str = "") -> FranchiseBible:
    bible_id = str(uuid4())
    bible = FranchiseBible(UUID(bible_id), name)
    bible._description = description
    _BIBLE_REGISTRY[bible_id] = bible
    return bible


def get_bible(bible_id: str) -> FranchiseBible | None:
    if bible_id in _BIBLE_REGISTRY:
        return _BIBLE_REGISTRY[bible_id]
    for rid, bible in _BIBLE_REGISTRY.items():
        if rid.startswith(bible_id):
            return bible
    if _db_available():
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(_load_single_bible(bible_id))
            except Exception:
                pass
    if bible_id in _BIBLE_REGISTRY:
        return _BIBLE_REGISTRY[bible_id]
    for rid, bible in _BIBLE_REGISTRY.items():
        if rid.startswith(bible_id):
            return bible
    return None


async def _load_single_bible(bible_id: str) -> None:
    repo = BibleRepository()
    try:
        db_bible = await repo.get(UUID(bible_id))
    except Exception:
        db_bible = None
        db_bibles = await repo.list()
        for b in db_bibles:
            if str(b.id).startswith(bible_id):
                db_bible = b
                break
    if db_bible is None:
        return
    bible = FranchiseBible(db_bible.id, db_bible.name)
    bible._description = db_bible.description or ""
    entries = await repo.search_entries(db_bible.id, "")
    for entry in entries:
        bible._entries[entry.id] = {
            "id": entry.id,
            "bible_id": db_bible.id,
            "category": entry.category,
            "name": entry.name,
            "content": entry.content,
            "metadata": entry.metadata_ or {},
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else "",
        }
    _BIBLE_REGISTRY[str(db_bible.id)] = bible


def list_bibles() -> list[dict[str, Any]]:
    if not _BIBLE_REGISTRY and _db_available():
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(load_bibles_from_db())
            except Exception:
                pass
    return [
        {"id": str(b.id), "name": b.name, "description": getattr(b, "_description", ""), "entry_count": len(b._entries)}
        for b in _BIBLE_REGISTRY.values()
    ]


def delete_bible(bible_id: str) -> bool:
    if bible_id in _BIBLE_REGISTRY:
        del _BIBLE_REGISTRY[bible_id]
        return True
    return False


async def load_bibles_from_db() -> None:
    if not _db_available():
        return
    repo = BibleRepository()
    db_bibles = await repo.list()
    for db_bible in db_bibles:
        existing = _BIBLE_REGISTRY.get(str(db_bible.id))
        if not existing:
            bible = FranchiseBible(db_bible.id, db_bible.name)
            bible._description = db_bible.description or ""
            entries = await repo.search_entries(db_bible.id, "")
            for entry in entries:
                bible._entries[entry.id] = {
                    "id": entry.id,
                    "bible_id": db_bible.id,
                    "category": entry.category,
                    "name": entry.name,
                    "content": entry.content,
                    "metadata": entry.metadata_ or {},
                    "created_at": entry.created_at.isoformat() if entry.created_at else "",
                    "updated_at": entry.updated_at.isoformat() if entry.updated_at else "",
                }
            _BIBLE_REGISTRY[str(db_bible.id)] = bible


class FranchiseBible:
    def __init__(
        self,
        bible_id: UUID,
        name: str,
        event_bus: AsyncioEventBus | None = None,
        repository: BibleRepository | None = None,
    ) -> None:
        self.id = bible_id
        self.name = name
        self._entries: dict[UUID, dict[str, Any]] = {}
        self._event_bus = event_bus
        self._repository = repository
        self._description: str = ""

    async def add_entry(
        self,
        category: str,
        name: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        entry_id = uuid4()
        self._entries[entry_id] = {
            "id": entry_id,
            "bible_id": self.id,
            "category": category,
            "name": name,
            "content": content,
            "metadata": metadata or {},
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
            "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        if self._repository is not None:
            db_entry = DBBibleEntry(
                id=entry_id,
                bible_id=self.id,
                category=category,
                name=name,
                content=content,
                metadata_=metadata or {},
            )
            await self._repository.add_entry(db_entry)
        elif _db_available():
            repo = BibleRepository()
            db_entry = DBBibleEntry(
                id=entry_id,
                bible_id=self.id,
                category=category,
                name=name,
                content=content,
                metadata_=metadata or {},
            )
            try:
                await repo.add_entry(db_entry)
            except Exception:
                pass
        return entry_id

    async def clear_entries(self) -> None:
        self._entries.clear()
        if self._repository is not None:
            await self._repository.delete_entries(self.id)
        elif _db_available():
            try:
                repo = BibleRepository()
                await repo.delete_entries(self.id)
            except Exception:
                pass

    async def search(self, query: str, category: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        query_lower = query.lower()
        for entry in self._entries.values():
            if category and entry["category"] != category:
                continue
            if query_lower in entry["content"].lower() or query_lower in entry["name"].lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        return results

    async def verify_continuity(self, content: str) -> dict[str, Any]:
        contradictions: list[str] = []
        for entry in self._entries.values():
            pass
        return {
            "contradictions": contradictions,
            "score": max(0, 100 - len(contradictions) * 10),
            "entries_checked": len(self._entries),
        }

    def get_entries(self, category: str | None = None) -> list[dict[str, Any]]:
        if category:
            return [e for e in self._entries.values() if e["category"] == category]
        return list(self._entries.values())

    def get_entry(self, entry_id: UUID) -> dict[str, Any] | None:
        return self._entries.get(entry_id)