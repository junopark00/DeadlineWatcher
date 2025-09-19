# Deadline Watcher Configuration and API

## Overview

Deadline Watcher is a Deadline Render Job monitoring tool used in the background of VFX artist PCs. \
It operates as a local server in the background and monitors specific jobs according to POST requests, \
executing predefined callbacks when jobs are completed.

## Project Structure

```
DeadlineWatcher/
├── start.py                    # Startup script (includes auto-registration to OS)
├── config/
│   └── settings.yaml           # YAML file containing configuration settings
├── watcher/
│   ├── api.py                  # FastAPI server - routes for job submission
│   ├── main.py                 # Periodic Deadline status checking
│   ├── monitor.py              # Job status checking via Deadline REST API
│   ├── handler.py              # Post-processing for completed jobs (video playback, etc.)
│   └── logger.py               # Logger configuration
```

## Usage

### 1. Starting the Application

```bash
python start.py
```

* On first run, automatically registers with OS (`Windows`: shell:startup, `macOS`: launchctl, `Linux`: autostart .desktop)
* Runs automatically thereafter

### 2. Job Registration from External Tools

```python
import requests

requests.post("http://127.0.0.1:21040/job", json={
    "job_id": "648b83fcd6b9e21324a8f347",
    "job_name": "NUKE_Render",
    "output_path": "C:/project/renders/output.mov",
    "plugin": "Nuke"
})
```

* `output_path` can be modified
* Registered jobs are periodically checked for status in `watcher/main.py`

### 3. Deadline Status Checking

* Queries the Repository defined in `config/settings.yaml`
* When status is `Completed`, executes post-processing via `watcher/handler.py`

### 4. Post-processing Logic

* If `output_path` is a video file, automatically plays it
* Otherwise, opens the corresponding folder
* Future extensions possible for message sending, etc.

## config/settings.yaml Configuration

```yaml
app:
  name: DeadlineWatcher
  check_interval_sec: 10                     # Job status check interval (seconds)
  retry_delay_sec: 5                         # Retry delay on exception (seconds)
  log_dir: "~/deadline_watcher/logs"         # Log directory
  log_file: "watcher.log"                    # Log file name
  job_file: "~/deadline_watcher/jobs.json"   # Job information file
  pid_file: "~/deadline_watcher/watcher.pid" # PID record file
  exe_file: "~/deadline_watcher/deadline_watcher.exe"  # Executable file

deadline:
  ip: "192.168.10.1"                       # Deadline Repository IP
  port: 8081                                 # Deadline Repository Port

api:
  host: "127.0.0.1"                          # FastAPI host
  port: 21040                                # FastAPI port
```
