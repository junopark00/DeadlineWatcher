# -*- coding: utf-8 -*-

import win32serviceutil
import win32service
import win32event
import subprocess
import os
import sys

class DeadlineWatcherService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DeadlineWatcherService"
    _svc_display_name_ = "Deadline Watcher Service"
    _svc_description_ = "Runs DeadlineWatcher start.py as a Windows service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process:
            self.process.terminate()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        python_exe = r"C:\MTHD_core\GlobalPython\python.exe"
        script_path = r"C:\MTHD_core\DeadlineWatcher\start.py"

        self.process = subprocess.Popen(
            [python_exe, script_path],
            stdout=open(os.path.join(os.path.expanduser("~"), "deadline_watcher", "logs", "service.log"), "a"),
            stderr=subprocess.STDOUT,
            shell=False
        )
        
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        if self.process:
            self.process.terminate()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        win32serviceutil.HandleCommandLine(DeadlineWatcherService)
    else:
        if sys.argv[1].lower() == "install":
            win32serviceutil.InstallService(
                cls=DeadlineWatcherService,
                serviceName=DeadlineWatcherService._svc_name_,
                displayName=DeadlineWatcherService._svc_display_name_,
                description=DeadlineWatcherService._svc_description_,
                startType=win32service.SERVICE_AUTO_START
            )
            print("Service installed as Automatic start.")
        else:
            win32serviceutil.HandleCommandLine(DeadlineWatcherService)