"""Testes de deduplicação."""

from __future__ import annotations

from careercompass.processing.dedup import dedup_jobs, dedup_stats


class TestDedupJobs:
    """Deduplicação por (fonte, url) ou (fonte, id)."""

    def test_no_duplicates(self) -> None:
        jobs = [
            {"fonte": "gupy", "id": "1", "url": "https://a.com/1"},
            {"fonte": "gupy", "id": "2", "url": "https://a.com/2"},
        ]
        result = dedup_jobs(jobs)
        assert len(result) == 2

    def test_duplicate_by_url(self) -> None:
        jobs = [
            {"fonte": "gupy", "id": "1", "url": "https://a.com/1"},
            {"fonte": "gupy", "id": "2", "url": "https://a.com/1"},  # mesma URL
        ]
        result = dedup_jobs(jobs)
        assert len(result) == 1

    def test_duplicate_by_id(self) -> None:
        jobs = [
            {"fonte": "geekhunter", "id": "vaga-abc"},
            {"fonte": "geekhunter", "id": "vaga-abc"},
        ]
        result = dedup_jobs(jobs)
        assert len(result) == 1

    def test_different_fonte_same_url(self) -> None:
        """Mesma URL em fontes diferentes = não é duplicata."""
        jobs = [
            {"fonte": "gupy", "id": "1", "url": "https://a.com/1"},
            {"fonte": "geekhunter", "id": "1", "url": "https://a.com/1"},
        ]
        result = dedup_jobs(jobs)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        assert dedup_jobs([]) == []


class TestDedupStats:
    """Estatísticas de dedup."""

    def test_stats(self) -> None:
        stats = dedup_stats(100, 85)
        assert stats["total_antes"] == 100
        assert stats["total_depois"] == 85
        assert stats["duplicatas_removidas"] == 15
