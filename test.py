# -*- coding: utf-8 -*-

import os
import sys
import traceback
import requests
import json

API_URL = "http://127.0.0.1:21040/job"


def submit_job(name_suffix, write_node, dependencies=None):
    deadline_con = DeadlineConnector()

    JobInfo = {
        "BatchName": "TEST_RENDER",
        "Name": f"TEST - {write_node} - {name_suffix}",
        "Plugin": "Nuke",
        "Pool": "io",
        "Priority": 100,
        "Frames": "1001-1101",
        "OutputDirectory0": "V:/TEST_film/TEST3",
        "OutputFilename0": f"{write_node}.{name_suffix}.####.exr",
        "UserName": os.environ.get("USERNAME"),
    }

    # ✅ 다중 종속성 처리
    if dependencies:
        if isinstance(dependencies, list):
            for idx, dep_id in enumerate(dependencies):
                JobInfo[f"JobDependency{idx}"] = dep_id
        elif isinstance(dependencies, str):
            JobInfo["JobDependency0"] = dependencies

    PluginInfo = {
        "Version": "14.1",
        "NukeX": True,
        "BatchMode": True,
        "SceneFile": "V:/TEST_film/TEST2/test.nk",
        "RenderMode": "Use Scene Settings",
        "WriteNode": write_node,
    }

    try:
        res = deadline_con.con.Jobs.SubmitJob(JobInfo, PluginInfo)
        job_id = res.get("_id")
        print(f"[+] Submitted: {JobInfo['Name']} (ID: {job_id})")
        return job_id, JobInfo["OutputDirectory0"] + "/" + JobInfo["OutputFilename0"], JobInfo["Plugin"], JobInfo["Name"]
    except Exception as e:
        print(f"[!] Submit Error: {e}")
        return None, "", "", ""


class DeadlineConnector():
    def __init__(self):
        # Use Deadline API
        from Deadline.DeadlineConnect import DeadlineCon as Connect
        self.con = Connect("192.168.10.101", 8081)

    @property
    def pools(self):
        return self.con.Pools.GetPoolNames()

    @property
    def machines(self):
        return [m for m in self.con.Slaves.GetSlaveNames() if m.startswith("ren")]


# 잡 등록 예시 (Nuke)
def register_nuke_job(job_id, output_path, plugin, job_name):
    payload = {
        "job_id": job_id,
        "output_path": output_path,
        "plugin": plugin,
        "job_name": job_name
    }
    response = requests.post(API_URL, json=payload)
    print("Nuke Job 등록 결과:", response.status_code, response.json())


# 잡 등록 예시 (Maya)
def register_maya_job():
    payload = {
        "job_id": "maya_test_002",
        "output_path": "C:/renders/maya_test_002.exr",
        "plugin": "Maya",
        "job_name": "Maya Render"
    }
    response = requests.post(API_URL, json=payload)
    print("Maya Job 등록 결과:", response.status_code, response.json())


# 잡 등록 예시 (Houdini)
def register_houdini_job():
    payload = {
        "job_id": "houdini_test_003",
        "output_path": "C:/renders/houdini_test_003.mkv",
        "plugin": "Houdini",
        "job_name": "Houdini FX"
    }
    response = requests.post(API_URL, json=payload)
    print("Houdini Job 등록 결과:", response.status_code, response.json())
    
def get_all_jobs():
    deadline_con = DeadlineConnector()
    all_jobs = deadline_con.con.Jobs.GetJobsInState(1)
    print(f"Total jobs: {len(all_jobs)}")


print(os.getpid())


if __name__ == "__main__":
    try:
        jobA_id, outA, pluginA, nameA = submit_job("A", "Write_exr1")
        register_nuke_job(jobA_id, outA, pluginA, nameA)
        jobB_id, outB, pluginB, nameB = submit_job("B", "Write_exr2")
        register_nuke_job(jobB_id, outB, pluginB, nameB)
        jobC_id, outC, pluginC, nameC = submit_job("C", "Write_exr3", dependencies=[jobA_id, jobB_id])
        register_nuke_job(jobC_id, outC, pluginC, nameC)
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()