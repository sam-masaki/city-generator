import time


class Stopwatch:
    def __init__(self):
        self.num_runs = 0
        self.total_ns = 0
        self.last_start = 0
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.num_runs += 1
            self.last_start = time.time_ns()  # should I use monotonic_ns()?
            self.is_running = True

    def stop(self):
        if self.is_running:
            self.total_ns += time.time_ns() - self.last_start
            self.is_running = False

    def reset(self):
        self.num_runs = 0
        self.total_ns = 0
        self.last_start = 0
        self.is_running = False

    def passed_ns(self) -> int:
        return self.total_ns

    def passed_ms(self) -> float:
        return self.total_ns / 1000000

    def passed_s(self) -> float:
        return self.total_ns / 1000000000

    def avg_ns(self) -> float:
        if self.num_runs == 0:
            return 0
        return self.total_ns / self.num_runs

    def avg_ms(self) -> float:
        if self.num_runs == 0:
            return 0
        return self.passed_ms() / self.num_runs

    def avg_s(self) -> float:
        if self.num_runs == 0:
            return 0
        return self.passed_s() / self.num_runs
