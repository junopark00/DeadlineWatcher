# -*- coding: utf-8 -*-

import time
from fastapi import FastAPI, HTTPException
from typing import Union
from pydantic import BaseModel
from watcher.config_loader import config
from watcher.logger import setup_logger
from watcher.jobs import *

logger = setup_logger()
app = FastAPI()

class JobInfo(BaseModel):
    job_id: str
    output_path: Union[str, list]
    plugin: str
    job_name: str

@app.post("/job")
async def register_job(job: JobInfo):
    from watcher.jobs import get_jobs_snapshot
    
    existing_jobs = get_jobs_snapshot()
    if any(j["job_id"] == job.job_id for j in existing_jobs):
        raise HTTPException(status_code=400, detail="Job already registered")
    
    job_data = job.dict()
    job_data["status"] = "Pending"
    job_data["registered_at"] = time.time()
    
    add_job(job_data)
    logger.info(f"[API] Registered job: {job.job_id} (plugin: {job.plugin})")
    return {"message": "Job registered", "job_id": job.job_id}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a job by its ID
    """
    from watcher.jobs import get_jobs_snapshot
    jobs = get_jobs_snapshot()
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "job_name": job.get("job_name"),
        "plugin": job.get("plugin"),
        "status": job.get("status", "Unknown"),
        "output_path": job.get("output_path"),
        "registered_at": job.get("registered_at")
    }

@app.get("/jobs")
async def list_jobs():
    """
    Get all registered jobs
    """
    from watcher.jobs import get_jobs_snapshot
    jobs = get_jobs_snapshot()
    return {"jobs": jobs, "count": len(jobs)}

@app.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """
    Delete a job by its ID
    """
    from watcher.jobs import get_jobs_snapshot, remove_job
    jobs = get_jobs_snapshot()
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    remove_job(job)
    logger.info(f"[API] Stop Watching job: {job_id}")
    return {"message": "Job monitoring cancelled"}

def start_api_server():
    import uvicorn
    try:
        uvicorn.run(app, host=config.api_host, port=config.api_port, use_colors=False)
        logger.info(f"[API] API server started at http://{config.api_host}:{config.api_port}")
    except Exception as e:
        logger.error(f"[API] Failed to start API server: {e}")
        logger.info(f"Retrying...")
        time.sleep(5)
        start_api_server()
