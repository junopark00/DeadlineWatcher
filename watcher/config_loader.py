# -*- coding: utf-8 -*-

import os
import yaml


class Config:
    def __init__(self, config_path="W:/MTHD_core/DeadlineWatcher/config/settings.yaml"):
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"[Error] Config file not found: {config_path}")

            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)

            self.app_name = cfg["app"].get("name", "Watcher")
            self.check_interval = cfg["app"].get("check_interval_sec", 10)
            self.retry_delay = cfg["app"].get("retry_delay_sec", 5)
            self.log_dir = os.path.expanduser(cfg["app"].get("log_dir", "~/logs"))
            self.log_file = cfg["app"].get("log_file", "watcher.log")
            self.job_file = os.path.expanduser(cfg["app"].get("job_file", "~/deadline_watcher/jobs.json"))
            self.pid_file = os.path.expanduser(cfg["app"].get("pid_file", "~/deadline_watcher/watcher.pid"))
            self.exe_file = rf'{(cfg["app"].get("exe_file", "//192.168.10.190/substorage/standalone/exe/deadline_watcher.exe"))}'

            self.deadline_ip = cfg["deadline"].get("ip", "127.0.0.1")
            self.deadline_port = cfg["deadline"].get("port", 8082)
            self.deadline_api = cfg["deadline"].get("api_url", None)  # legacy, not used

            self.api_host = cfg["api"].get("host", "127.0.0.1")
            self.api_port = cfg["api"].get("port", 5050)

        except Exception as e:
            raise RuntimeError(f"[Error] Failed to load config: {e}")


config = Config()