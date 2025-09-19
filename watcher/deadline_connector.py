# -*- coding: utf-8 -*-

import Deadline.DeadlineConnect as DeadlineConnect
from watcher.config_loader import config


class DeadlineConnector:
    def __init__(self):
        self.con = DeadlineConnect.DeadlineCon(
            config.deadline_ip,
            config.deadline_port
        )
