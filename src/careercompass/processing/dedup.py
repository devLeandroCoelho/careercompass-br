"""Deduplicação de vagas por chave natural (fonte, url) ou (fonte, id)."""

from __future__ import annotations

from typing import Any


def _make_key(job: dict[str, Any]) -> str:
    """Gera chave de dedup. Prioriza (fonte, url); se não houver url, usa (fonte, id)."""
    fonte = job.get("fonte", "")
    url = job.get("url")
    job_id = job.get("id", "")
    if url:
        return f"{fonte}|url={url}"
    return f"{fonte}|id={job_id}"


def dedup_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicatas mantendo a primeira ocorrência.

    Args:
        jobs: lista de dicts normalizados.

    Returns:
        Lista sem duplicatas.
    """
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []

    for job in jobs:
        key = _make_key(job)
        if key not in seen:
            seen.add(key)
            unique.append(job)

    return unique


def dedup_stats(total: int, unique: int) -> dict[str, int]:
    """Retorna estatísticas de dedup."""
    return {
        "total_antes": total,
        "total_depois": unique,
        "duplicatas_removidas": total - unique,
    }
