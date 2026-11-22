"""Sample CPU and memory usage for a process and its descendants."""

import threading
import time


def measure_process_tree(function, *args, **kwargs):
    """Run function and return its value plus sampled process-tree utilization."""
    try:
        import psutil
    except ImportError:
        return function(*args, **kwargs), {
            "cpu_avg_pct": None,
            "cpu_peak_pct": None,
            "memory_avg_pct": None,
            "memory_peak_pct": None,
            "measurement": "psutil tidak terpasang",
        }

    root = psutil.Process()
    cpu_count = psutil.cpu_count() or 1
    try:
        total_memory = psutil.virtual_memory().total
    except (OSError, psutil.Error):
        total_memory = 0

    samples = []
    sample_lock = threading.Lock()
    stop = threading.Event()

    def sample():
        processes = [root]
        try:
            processes.extend(root.children(recursive=True))
        except (psutil.Error, OSError):
            pass
        cpu_percent = 0.0
        rss_bytes = 0
        for process in processes:
            try:
                cpu_percent += process.cpu_percent(interval=None)
                rss_bytes += process.memory_info().rss
            except (psutil.Error, OSError):
                continue
        memory_percent = rss_bytes * 100 / total_memory if total_memory else 0.0
        with sample_lock:
            samples.append((cpu_percent / cpu_count, memory_percent))

    def sampler():
        while not stop.wait(0.2):
            sample()

    # Prime psutil's per-process CPU counters before measuring the task.
    try:
        root.cpu_percent(interval=None)
        for process in root.children(recursive=True):
            process.cpu_percent(interval=None)
    except (psutil.Error, OSError):
        pass

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    try:
        result = function(*args, **kwargs)
    finally:
        stop.set()
        thread.join()
        sample()

    with sample_lock:
        observed = list(samples)
    if not observed:
        observed = [(0.0, 0.0)]
    cpu_values = [entry[0] for entry in observed]
    memory_values = [entry[1] for entry in observed]
    return result, {
        "cpu_avg_pct": sum(cpu_values) / len(cpu_values),
        "cpu_peak_pct": max(cpu_values),
        "memory_avg_pct": sum(memory_values) / len(memory_values),
        "memory_peak_pct": max(memory_values),
        "measurement": "proses + seluruh child process; CPU % dari total core, RAM % dari total memori",
    }
