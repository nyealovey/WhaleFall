"""
Scheduler health inspection utilities.

Encapsulates all logic needed to evaluate APScheduler state without
depending on private attributes that may not exist in every scheduler
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from apscheduler.schedulers.base import BaseScheduler


@dataclass
class ExecutorReport:
    """Represents the outcome of a single executor inspection."""

    name: str
    class_name: str
    healthy: bool
    details: str | None = None


@dataclass
class SchedulerHealthReport:
    """Aggregated scheduler health information."""

    scheduler_running: bool
    total_jobs: int
    running_jobs: int
    paused_jobs: int
    executors: List[ExecutorReport] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def executor_working(self) -> bool:
        """True if at least one executor passes inspection."""
        return any(report.healthy for report in self.executors)


class SchedulerHealthService:
    """Collects runtime information from APScheduler instances."""

    def inspect(self, scheduler: BaseScheduler | None) -> SchedulerHealthReport:
        """
        Inspect scheduler status and executors.

        Args:
            scheduler: Scheduler instance produced by TaskScheduler.

        Returns:
            SchedulerHealthReport describing the current runtime state.
        """
        if not scheduler:
            return SchedulerHealthReport(
                scheduler_running=False,
                total_jobs=0,
                running_jobs=0,
                paused_jobs=0,
                warnings=["scheduler_not_available"],
            )

        warnings: List[str] = []
        try:
            jobs = scheduler.get_jobs()
        except Exception as exc:  # pragma: no cover - defensive runtime protection
            warnings.append("jobstore_unreachable")
            jobs = []
        running_jobs = [job for job in jobs if job.next_run_time is not None]
        paused_jobs = [job for job in jobs if job.next_run_time is None]

        executor_reports, executor_warnings = self._inspect_executors(scheduler)
        warnings.extend(executor_warnings)

        return SchedulerHealthReport(
            scheduler_running=bool(getattr(scheduler, "running", False)),
            total_jobs=len(jobs),
            running_jobs=len(running_jobs),
            paused_jobs=len(paused_jobs),
            executors=executor_reports,
            warnings=warnings,
        )

    def _inspect_executors(
        self, scheduler: BaseScheduler
    ) -> Tuple[List[ExecutorReport], List[str]]:
        """
        Inspect available executors using public APIs when possible.

        Returns:
            Tuple of (executor reports, warnings)
        """
        reports: List[ExecutorReport] = []
        warnings: List[str] = []

        # APScheduler keeps executors in a private dict, but also exposes helper
        # methods that are consistent across schedulers. We try official helpers
        # first, then gracefully fall back to private attributes if necessary.
        executor_sources: List[Tuple[str, Any]] = []

        # 1) Attempt to list known executor aliases from scheduler state
        try:
            executor_sources = list(getattr(scheduler, "_executors", {}).items())
        except Exception:  # pragma: no cover - defensive: attribute missing
            executor_sources = []

        # 2) If nothing was collected, probe common aliases through lookups
        if not executor_sources:
            for alias in ("default", "processpool"):
                try:
                    executor = scheduler.lookup_executor(alias)  # type: ignore[attr-defined]
                    if executor:
                        executor_sources.append((alias, executor))
                except AttributeError:
                    # lookup_executor only exists on newer APScheduler versions
                    try:
                        executor = scheduler._lookup_executor(alias)  # type: ignore[attr-defined]
                    except Exception:
                        executor = None
                    if executor:
                        executor_sources.append((alias, executor))
                except Exception:
                    warnings.append(f"executor_lookup_failed:{alias}")

        if not executor_sources:
            warnings.append("no_executors_detected")

        for alias, executor in executor_sources:
            if not executor:
                reports.append(
                    ExecutorReport(
                        name=alias,
                        class_name="UnknownExecutor",
                        healthy=False,
                        details="executor_object_missing",
                    )
                )
                continue

            class_name = executor.__class__.__name__
            healthy = getattr(executor, "shutdown", None) is not None
            reports.append(
                ExecutorReport(
                    name=alias,
                    class_name=class_name,
                    healthy=healthy,
                    details=None if healthy else "executor_missing_shutdown",
                )
            )

        return reports, warnings


scheduler_health_service = SchedulerHealthService()
