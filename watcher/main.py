# -*- coding: utf-8 -*-

import time
import threading
import traceback
from importlib import reload
from watcher import handler
from watcher.logger import setup_logger
from watcher.monitor import DeadlineMonitor
from watcher.config_loader import config
from watcher.jobs import get_jobs_snapshot, remove_job, update_job_status

logger = setup_logger()

class JobWatcher(threading.Thread):
    def __init__(self, job, interval=10):
        super().__init__(daemon=True)
        self.job = job
        self.job_id = job.get("job_id")
        self.interval = interval
        self.monitor = DeadlineMonitor()
        self._stop_event = threading.Event()

    def run(self):
        logger.info(f"[JobWatcher] Wathching job: {self.job_id} (plugin: {self.job.get('plugin', 'Unknown')})")
        while not self._stop_event.is_set():
            try:
                job_details = self.monitor.get_job_details(self.job_id)
                status = job_details["status"]

                if status == "Error":
                    logger.warning(f"[JobWatcher] Job {self.job_id} removed/deleted from Deadline.")
                    remove_job(self.job)
                    break

                if job_details["total_chunks"] > 0:
                    progress_pct = (job_details["progress"] / job_details["total_chunks"]) * 100
                    logger.debug(f"{self.job_id} Status: {status} ({progress_pct:.1f}%)")
                else:
                    logger.debug(f"{self.job_id} Status: {status}")

                if get_jobs_snapshot() and any(j.get("job_id") == self.job_id for j in get_jobs_snapshot()):
                    update_job_status(self.job, status, job_details)

                if self.monitor.is_job_completed(status):
                    logger.info(f"[COMPLETE] {self.job_id}. Running post-processing...")
                    reload(handler)
                    handler.handle_completed_job(self.job)
                    remove_job(self.job)
                    break

                elif self.monitor.is_job_failed(status):
                    logger.warning(f"[FAILED] {self.job_id}. Job failed with errors: {job_details.get('errors', [])}")
                    remove_job(self.job)
                    break

            except Exception as e:
                logger.error(f"[JobWatcher] Traceback for job {self.job_id}: {e}")
                traceback.print_exc()

            time.sleep(self.interval)

    def stop(self):
        self._stop_event.set()


class JobWatchManager:
    def __init__(self, interval=None):
        self.interval = interval or config.check_interval
        self.watchers = {}
        self.lock = threading.Lock()

    def start_watching(self):
        logger.info("[JobWatchManager] Starting job watch manager")
        while True:
            jobs = get_jobs_snapshot()
            with self.lock:
                if not jobs:
                    for watcher in self.watchers.values():
                        watcher.stop()
                    self.watchers.clear()
                    time.sleep(1)
                    continue
                for job in jobs:
                    job_id = job.get("job_id")
                    if job_id not in self.watchers:
                        watcher = JobWatcher(job, interval=self.interval)
                        self.watchers[job_id] = watcher
                        watcher.start()
                for job_id in list(self.watchers.keys()):
                    if not any(j.get("job_id") == job_id for j in jobs):
                        watcher = self.watchers.pop(job_id)
                        watcher.stop()
            time.sleep(1)

def run_watcher():
    manager = JobWatchManager()
    manager.start_watching()
