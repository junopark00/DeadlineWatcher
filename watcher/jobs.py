# -*- coding: utf-8 -*-

import time
import json
import threading
from watcher.config_loader import config
from watcher.logger import setup_logger

logger = setup_logger()
jobs_lock = threading.Lock()

def _load_jobs():
    try:
        with jobs_lock:
            with open(config.job_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except FileNotFoundError:
        with open(config.job_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[JOBS] Failed to load jobs: {e}")        
        return []

def _save_jobs(jobs):
    with jobs_lock:
        with open(config.job_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)

def add_job(job_data):
    jobs = _load_jobs()
    jobs.append(job_data)
    _save_jobs(jobs)

def remove_job(job_data):
    jobs = _load_jobs()
    jobs = [j for j in jobs if j.get("job_id") != job_data.get("job_id")]
    _save_jobs(jobs)

def get_jobs_snapshot():
    return _load_jobs()

def update_job_status(job, status, details=None):
    jobs = _load_jobs()
    for j in jobs:
        if j.get("job_id") == job.get("job_id"):
            j["status"] = status
            j["last_check"] = time.time()
            if details:
                j["progress"] = details.get("progress", 0)
                j["total_chunks"] = details.get("total_chunks", 0)
                j["errors"] = details.get("errors", [])
                j["frames"] = details.get("frames", {})
    _save_jobs(jobs)

def find_job_by_id(job_id):
    jobs = _load_jobs()
    return next((job for job in jobs if job.get("job_id") == job_id), None)

def get_job_stats():
    jobs = _load_jobs()
    total = len(jobs)
    if total == 0:
        return {"total": 0, "by_status": {}}
    stats = {"total": total, "by_status": {}}
    for job in jobs:
        status = job.get("status", "Unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
    return stats
