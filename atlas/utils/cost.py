from __future__ import annotations

import resource
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class CostTracker:
    """Track wall-clock and CPU usage for a single pipeline evaluation."""

    start_wall: float = time.perf_counter()
    start_cpu: float = time.process_time()

    def snapshot(self) -> Dict[str, float]:
        wall = time.perf_counter() - self.start_wall
        cpu = time.process_time() - self.start_cpu
        usage = resource.getrusage(resource.RUSAGE_SELF)
        max_rss = getattr(usage, "ru_maxrss", 0.0)
        return {"wall_seconds": wall, "cpu_seconds": cpu, "max_rss_kb": float(max_rss)}
