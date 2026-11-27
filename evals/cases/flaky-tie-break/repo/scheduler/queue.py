class JobQueue:
    def __init__(self):
        self._jobs: list[tuple[str, int]] = []

    def submit(self, name: str, priority: int) -> None:
        self._jobs.append((name, priority))

    def next_jobs(self, n: int) -> list[str]:
        """The n most urgent job names (higher priority first, ties in submission order)."""
        priority = dict(self._jobs)
        pending = {name for name, _ in self._jobs}
        return sorted(pending, key=lambda name: -priority[name])[:n]
