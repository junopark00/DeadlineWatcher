# -*- coding: utf-8 -*-

import os
import sys
import time
import requests
import subprocess
from watcher.logger import setup_logger
from watcher.utils import get_latest_rv_path

logger = setup_logger()

def handle_completed_job(job):
    try:
        job_name = job.get("name", "Unnamed")
        job_id = job.get("job_id")
        output_path = job.get("output_path")
        callback_url = job.get("callback_url")
        webhook_data = job.get("webhook_data", {})
    except Exception as e:
        logger.error(f"[HANDLE] Failed to extract job details: {e} | job: {job}")
        return

    logger.info(f"[HANDLE] Handling completed job: {job_id} | {job_name} | Output: {output_path}")

    if callback_url:
        try:
            send_completion_callback(job_id, job_name, output_path, callback_url, webhook_data)
        except Exception as e:
            logger.error(f"[HANDLE] Failed to send completion callback: {e} | job: {job}")

    plugin = job.get("plugin", "Unknown").lower()

    if isinstance(output_path, list):
        output_path = output_path[0]
    if not output_path or not os.path.exists(output_path):
        logger.warning(f"[HANDLE] Invalid output path: {output_path} | job: {job}")
        return

    try:
        if plugin == "nuke":
            logger.info(f"[HANDLE] NUKE post-processing... {output_path}")
            postprocess_nuke(job)
        elif plugin == "maya":
            logger.info(f"[HANDLE] Maya post-processing... {output_path}")
            postprocess_maya(job)
        elif plugin == "houdini":
            logger.info(f"[HANDLE] Houdini post-processing... {output_path}")
            postprocess_houdini(job)
        elif plugin == "python":
            logger.info(f"[HANDLE] Python Script post-processing... {output_path}")
            postprocess_python(job)
        elif plugin == "autotrack":
            logger.info(f"[HANDLE] AutoTrack post-processing... {output_path}")
            postprocess_autotrack(job)
        else:
            if output_path.lower().endswith((".mov", ".mp4", ".avi", ".mxf", ".mkv", ".exr", ".dpx")):
                logger.info(f"[HANDLE] Playing video: {output_path}")
                play_video(output_path)
            else:
                logger.info(f"[HANDLE] Opening folder: {os.path.dirname(output_path)}")
                open_folder(os.path.dirname(output_path))

    except Exception as e:
        logger.error(f"[HANDLE] Failed to handle completed job: {e} | job: {job}")

def postprocess_nuke(job):
    try:
        output_path = job.get("output_path")
        if output_path.lower().endswith(".mov"):
            rv_path = get_latest_rv_path()
            if not rv_path:
                from PySide6.QtWidgets import QMessageBox, QApplication
                app = QApplication([])
                QMessageBox.critical(None, "Error", "RV가 설치되어 있지 않아 파일을 열 수 없습니다.")
                app.exec_()
                return
            logger.info(f"[NUKE] Run RV for output: {output_path}")
            subprocess.Popen([rv_path, output_path])
    except Exception as e:
        logger.error(f"[NUKE] Failed to post-process Nuke job: {e} | job: {job}")

def postprocess_maya(job):
    # try:
    #     output_path = job.get("output_path")
    #     logger.info(f"[MAYA] Opening output folder: {output_path}")
    #     open_folder(os.path.dirname(output_path))
    # except Exception as e:
    #     logger.error(f"[MAYA] Failed to open output folder: {e} | job: {job}")
    pass

def postprocess_houdini(job):
    # try:
    #     output_path = job.get("output_path")
    #     logger.info(f"[HOUDINI] Post-processing for Houdini job: {output_path}")
    # except Exception as e:
    #     logger.error(f"[HOUDINI] Failed to post-process Houdini job: {e} | job: {job}")
    pass

def postprocess_autotrack(job):
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance()
        need_exec = False
        if not app:
            app = QApplication([])
            need_exec = True    
                    
        output_path = job.get("output_path")
        job_name = job.get('job_name')
        if isinstance(output_path, list):
            path = output_path[0]
            python_script_path = output_path[1]
            nuke_output_path = f'{path}/scenes/{job_name}.nk'
            if not os.path.exists(python_script_path) and os.path.exists(nuke_output_path):
                QMessageBox.information(None, "Job Finished", "Auto Track이 완료되었습니다.")
                logger.info(f"[AutoTrack] Auto Track completed successfully.")
            else:
                QMessageBox.warning(None, "Error", f"Auto Track이 중단되었습니다.\n로그파일을 확인하여 주세요.")
                logger.error(f"[AutoTrack] Auto Track failed or was interrupted. Check log file.")
                
            open_folder(os.path.dirname(path))
            logger.info(f"[AutoTrack] Opening output folder: {os.path.dirname(path)}")
            
            if need_exec:
                app.exec_()
            return
        
    except Exception as e:
        import traceback
        logger.error(f"[AutoTrack] Failed to execute Python script: {e} | job: {job}")
        logger.error(traceback.format_exc())
        
def postprocess_python(job):
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        app = QApplication([])
        
        output_path = job.get("output_path")
        job_name = job.get('job_name')
        if isinstance(output_path, list):
            path = output_path[0]
            python_script_path = output_path[1]
            nuke_output_path = f'{path}/scenes/{job_name}.nk'
            if not os.path.exists(python_script_path) and os.path.exists(nuke_output_path):
                QMessageBox.information(None, "Job Finished", "Auto Track이 완료되었습니다.")
            else:
                QMessageBox.warning(None, "Error", f"Auto Track이 중단되었습니다.\n로그파일을 확인하여 주세요.")
                
            open_folder(os.path.dirname(path))
            app.exec_()
            return
        
    except Exception as e:
        logger.error(f"[PYTHON] Failed to execute Python script: {e} | job: {job}")

def send_completion_callback(job_id, job_name, output_path, callback_url, webhook_data):
    """완료 콜백 전송"""
    try:
        payload = {
            "job_id": job_id,
            "job_name": job_name,
            "status": "completed",
            "output_path": output_path,
            "completed_at": time.time(),
            **webhook_data
        }
        
        response = requests.post(
            callback_url, 
            json=payload, 
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        logger.info(f"[CALLBACK] Successfully sent callback to {callback_url} for job {job_id}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"[CALLBACK] Failed to send callback: {e} | job_id: {job_id} | callback_url: {callback_url}")
    except Exception as e:
        logger.error(f"[CALLBACK] Unexpected error while sending callback: {e} | job_id: {job_id} | callback_url: {callback_url}")


def play_video(path):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif sys.platform == "darwin":  # macOS
            subprocess.Popen(["open", path])
        else:  # Linux or other
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        logger.error(f"[PLAY_VIDEO] Failed to play video: {e} | path: {path}")


def open_folder(folder_path):
    try:
        if os.name == 'nt':
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])
    except Exception as e:
        logger.error(f"[OPEN_FOLDER] Failed to open folder: {e} | folder_path: {folder_path}")