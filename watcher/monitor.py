# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from watcher.logger import setup_logger
from watcher.config_loader import config
from watcher.deadline_connector import DeadlineConnector

logger = setup_logger()

class DeadlineMonitor:
    def __init__(self):
        self.con = DeadlineConnector().con

    def get_job_details(self, job_id):
        STATUS_MAP = {
            0: "Queued",
            1: "Rendering",
            2: "Suspended",
            3: "Completed",
            4: "Failed",
            5: "Unknown",
            6: "Pending"
        }

        try:
            job_data = self.con.Jobs.GetJob(job_id)

            raw_status = job_data.get("Stat", 5)
            status_str = STATUS_MAP.get(raw_status, "Unknown")

            completed = job_data.get("CompletedChunks", 0)
            rendering = job_data.get("RenderingChunks", 0)
            queued = job_data.get("QueuedChunks", 0)

            total_chunks = completed + rendering + queued

            return {
                "status": status_str,
                "progress": completed,
                "total_chunks": total_chunks,
                "remaining_chunks": queued,
                "errors": job_data.get("Errs", 0),
                "render_time": job_data.get("Props", {}).get("JobRenderTime", 0),
                "last_updated": job_data.get("Date", ""),
                "frames": {
                    "completed": job_data.get("Props", {}).get("JobCompletedTasks", 0),
                    "total": job_data.get("Props", {}).get("Tasks", 0),
                    "failed": job_data.get("Props", {}).get("JobFailedTasks", 0)
                }
            }
        except Exception as e:
            return {
                "status": "Error",
                "progress": 0,
                "total_chunks": 0,
                "remaining_chunks": 0,
                "errors": [str(e)]
            }

    def is_job_completed(self, status):
        return status.lower() in ["completed"]

    def is_job_failed(self, status):
        return status.lower() in ["failed", "error", "cancelled", "aborted", "deleted"]


if __name__ == "__main__":
    monitor = DeadlineMonitor()
    job_id = '6875c0793a08713ae4d69a6f'

    status = monitor.get_job_status(job_id)
    print(f"Job {job_id} 상태: {status}")

    details = monitor.get_job_details(job_id)
    print(f"Job {job_id} 상세 정보: {details}")