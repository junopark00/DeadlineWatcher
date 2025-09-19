# -*- coding: utf-8 -*-

import os
import re
import sys
from Deadline_api.DeadlineConnect import DeadlineCon as Connect

# Custom Modules
try:
    import constants
    import deadline_constants
    import sg_manager
    from init_logger import IOManagerLogger
except:
    from pymodules import constants
    from pymodules import deadline_constants
    from pymodules import sg_manager
    from pymodules.init_logger import IOManagerLogger

# Set Logger
logger = IOManagerLogger(os.path.basename(__file__), constants.LOG_PATH)


class DeadlineManager():
    def __init__(self, username):
        self.ip = deadline_constants.DEADLINE_IP
        self.port = deadline_constants.DEADLINE_PORT
        self.pool = deadline_constants.DEADLINE_POOL
        self.sec_pool = deadline_constants.DEADLINE_SEC_POOL
        self.nuke_version = deadline_constants.DEADLINE_NUKE_VERSION
        self.nuke_path = deadline_constants.DEADLINE_NUKE_PATH
        self.python_version = deadline_constants.DEADLINE_PYTHON_VERSION
        self.username = username
        
        try:
            self.deadline = Connect(self.ip, int(self.port))
            os.environ["NO_PROXY"] = f"{self.ip}:{self.port}"
        except Exception as e:
            logger.error(f"Failed to connect to Deadline: {e}")
            return
        
    def submit_nuke_py_to_deadline(self, script_path, job_name, priority, depen_list=[], grp_name=''):
        job = {
            'UserName': self.username,
            'Name': job_name,
            'BatchName': grp_name,
            'Pool': self.pool,
            'SecondaryPool': self.sec_pool,
            'Priority': priority,
            'Plugin': 'CommandLine',
            'ChunkSize': 1,
            'Frames': 0,
            'ResumeOnCompleteDependencies': True,
            'ResumeOnDeletedDependencies': False,
            'ResumeOnFailedDependencies': False,
        }
        
        plugin = {
            'Shell': 'default',
            'ShellExecute': False,
            'SingleFramesOnly': True,
            'StartupDirectory': os.path.dirname(script_path),
            'Executable': self.nuke_path,
            'Arguments': f'--nukex -it "{script_path}"',
        }
        
        for idx, dep_id in enumerate(depen_list):
            job[f'JobDependency{idx}'] = dep_id
            
        deadline_job = self.deadline.Jobs.SubmitJob(job, plugin, idOnly=True)
        return deadline_job['_id']
    
    def submit_nuke_to_deadline(
        self, nk_path, row_data, render_settings, depen_list=[], grp_name="", 
        export_plate=False, export_jpg=True, export_mov=True
        ):
        
        start_frame = int(row_data.get('Start Frame')) if row_data.get('Start Frame') else 0
        end_frame = int(row_data.get('End Frame')) if row_data.get('End Frame') else 0
        priority = int(render_settings.get('priority')) if render_settings.get('priority') else 50
        
        # Job configuration
        job = {
            'UserName': self.username,
            'BatchName': grp_name,
            'Pool': self.pool,
            'SecondaryPool': self.sec_pool,
            'Priority': priority,
            'Plugin': 'Nuke',
            'ConcurrentTasks': 1,
            'ResumeOnCompleteDependencies': True,
            'ResumeOnDeletedDependencies': False,
            'ResumeOnFailedDependencies': False,
        }
        
        # Plugin configuration
        plugin = {
            'Version': self.nuke_version,
            'NukeX': True,
            'BatchMode': True,
            'BatchModeIsMovie': True,
            'Threads': 0,
            'RamUse': 0,
            'UseGpu': True,
            'GpuOverride': 0,
            'RenderMode': 'Use Scene Settings',
            'EnforceRenderOrder': False,
            'ContinueOnError': False,
            'Arguments': '-i',
            'SceneFile': nk_path,
        }
        
        # Add dependencies to the job
        depen_idx = 0
        for idx, dep_id in enumerate(depen_list):
            job[f'JobDependency{idx}'] = dep_id
            depen_idx += 1
            
        file_header = os.path.splitext(os.path.basename(nk_path))[0].replace('.render_', '')
        
        plate_id_list = []
        if export_plate:
            plate_id_list = self.submit_seq_job(job, plugin, 'WritePLATE', 'PLATE', start_frame, end_frame, file_header)
            
        jpg_id_list = []
        if export_jpg:
            jpg_id_list = self.submit_seq_job(job, plugin, 'WriteJPG', 'JPG', start_frame, end_frame, file_header)
            
        mov_job = {}
        if export_mov:
            mov_job = self.submit_mov_job(job, plugin, 'WriteMOV', 'MOV', start_frame, end_frame, file_header, priority)
        
        return plate_id_list, jpg_id_list, mov_job.get('_id', '')

    def submit_seq_job(self, job, plugin, write_node, tag, start_frame, end_frame, file_header):
        # Submit a sequence job
        plugin['WriteNode'] = write_node
        job['ChunkSize'] = 10
        job['ConcurrentTasks'] = 4
        
        frame_groups = self.split_frame_groups(start_frame, end_frame)
        
        job_id_list = []
        for idx, (s_frame, e_frame) in enumerate(frame_groups):
            job['Name'] = f"[{file_header}] - {tag}{idx+1}"
            job['Frames'] = f'{s_frame}-{e_frame}'
            job_id = self.deadline.Jobs.SubmitJob(job, plugin, idOnly=True)
            job_id_list.append(job_id['_id'])
        
        return job_id_list
    
    def submit_mov_job(self, job, plugin, write_node, tag, start_frame, end_frame, file_header, priority):
        # Submit a single frame job
        plugin['WriteNode'] = write_node
        job['Name'] = f"[{file_header}] - {tag}"
        job['Frames'] = f"{start_frame}-{end_frame}"
        job['ChunkSize'] = end_frame - start_frame + 1
        job['Priority'] = max(priority -1, 0)
        job['ConcurrentTasks'] = 1
        
        return self.deadline.Jobs.SubmitJob(job, plugin, idOnly=True)
    
    def split_frame_groups(self, start_frame, end_Frame, chunk_size=5000):
        # Split the frame range into groups of chunk_size.
        total_frames = end_Frame - start_frame + 1
        frame_groups = []
        
        if total_frames <= chunk_size:
            return [(start_frame, end_Frame)]
        
        # If the total frames are greater than the chunk size, split the frames into groups
        while total_frames > chunk_size:
            s_frame = start_frame
            e_frame = s_frame + chunk_size - 1
            frame_groups.append((s_frame, e_frame))
            start_frame = e_frame + 1
            total_frames -= chunk_size
        
        # Add the remaining frames to the last group 
        frame_groups.append((start_frame, end_Frame))
        
        return frame_groups
    
    def submit_copy_job(self, copy_data, script_path, priority=50, depen_list=[], grp_name=''):
        # Submit a Deadline job to copy files or directories
        total_files = len(copy_data)
        zfill = len(str(total_files))
        split_idx = 50
        script_list, script_idx = [], 1
        script_header = os.path.splitext(script_path)[0]

        # Helper function to create a new Python script command block
        def _create_copy_command(i, total, src, dest):
            cmd = f"print('({str(i+1).zfill(zfill)}/{total}) from {os.path.basename(src)} to {os.path.basename(dest)}')\n"
            cmd += f"shutil.copyfile('{src}', '{dest}')\n"
            return cmd

        # Generate and write the Python copy scripts
        cmd = ""
        for i, (target, dest) in enumerate(copy_data.items()):
            cmd += "import os\nimport sys\nimport shutil\n"
            cmd += _create_copy_command(i, total_files, target, dest)
            if (i % split_idx == split_idx - 1) or (i + 1 == total_files):
                _py = f"{script_header}_{script_idx:02}.py"
                with open(_py, 'w') as f:
                    f.write(cmd)
                script_list.append(_py)
                cmd, script_idx = "", script_idx + 1

        # If del_self flag is True, add a script for deleting the generated Python scripts
        # if cleanup_script:
        #     _py = script_header + '_remove_cmd.py'
        #     del_cmd = "import os\n" + "".join([f"os.remove('{p}')\n" for p in script_list])
        #     with open(_py, 'w') as f:
        #         f.write(del_cmd)
        #     script_list.append(_py)

        # Define the Deadline job information
        job_name = f'Copy from {os.path.basename(os.path.dirname(next(iter(copy_data))))}'
        grp_name = grp_name or job_name

        job = {
            'UserName': self.username,
            'Name': f'[{os.path.basename(os.path.dirname(dest))}] - {job_name}',
            'BatchName': grp_name,
            'Pool': self.pool,
            'SecondaryPool': self.sec_pool,
            'Priority': priority,
            'Plugin': 'Python',
            'ChunkSize': 1,
            'Frames': 1,
            'ConcurrentTasks': 4,
            'ResumeOnCompleteDependencies': True,
            'ResumeOnDeletedDependencies': False,
            'ResumeOnFailedDependencies': False
        }

        # Add job dependencies
        for idx, dep_id in enumerate(depen_list):
            job[f'JobDependency{idx}'] = dep_id

        # Submit each Python script to Deadline
        copy_id_list = []
        for idx, py_path in enumerate(script_list):
            plugin = {
                'SingleFramesOnly': True,
                'Version': self.python_version,
                'ScriptFile': py_path
            }

            job['Name'] = f'[{os.path.basename(os.path.dirname(dest))}] - {idx+1}_{job_name}'
            copy_job = self.deadline.Jobs.SubmitJob(job, plugin, idOnly=True)
            copy_id_list.append(copy_job['_id'])

        return copy_id_list
    
    def submit_sg_upload_to_deadline(self, ver_dict, input_file, proxy_mov, row_data, render_settings, depen_list=[], grp_name='', remove_mov=False):
        """Deadline을 통해 ShotGrid에 Version 업로드"""
        # ShotGrid 업로드 스크립트 생성
        first_frame = row_data.get('Start Frame')
        last_frame = row_data.get('End Frame')
        fps = render_settings.get('fps')
        priority = render_settings.get('priority')
        
        sg_py = self._write_sg_upload_script(ver_dict, input_file, proxy_mov, first_frame, last_frame, fps, remove_mov)

        if not grp_name:
            grp_name = self._extract_file_header(input_file) + ' - Version'

        job = self._create_deadline_job(grp_name, priority, depen_list)

        plugin = {
            'SingleFramesOnly': True,
            'Version': self.python_version,
            'ScriptFile': sg_py,
        }

        sg_job = self.deadline.Jobs.SubmitJob(job, plugin, idOnly=True)
        return sg_job['_id']

    def _write_sg_upload_script(self, ver_dict, input_file, proxy_mov, first_frame, last_frame, fps, remove_mov):
        """ShotGrid 업로드 스크립트를 작성하는 함수"""
        file_header = self._extract_file_header(input_file)
        upload_script = os.path.join(os.path.dirname(input_file), f"{file_header}_SG_Upload.py")
        logger.debug(f"SG Upload Script: {upload_script}")

        cmd = self._create_sg_upload_script_content(ver_dict, input_file, proxy_mov, first_frame, last_frame, fps, remove_mov, upload_script)

        with open(upload_script, 'w', encoding='utf-8') as f:
            f.write(cmd)

        return upload_script

    def _extract_file_header(self, input_file):
        """입력 파일에서 파일 헤더를 추출하는 함수"""
        p = re.compile(r'((.+)([_|.])([#]+|[%][0-9][0-9][d])[.](.+))')
        match = p.match(os.path.basename(input_file))
        if match:
            return match.group(2)
        return os.path.splitext(os.path.basename(input_file))[0]


    def _create_sg_upload_script_content(
        self, ver_dict, input_file, proxy_mov, start_frame, end_frame, fps, remove_mov: bool, upload_script
        ):
        """ShotGrid 업로드 스크립트의 내용을 생성하는 함수"""
        cmd = f"""# -*- coding:utf-8 -*-
SG_DOMAIN = "{sg_manager.get_base_url()}"
SESSION_TOKEN = "{sg_manager.get_session_token()}"
fps = {fps}
first_frame = {start_frame}
last_frame = {end_frame}
ver_dict = {ver_dict}
input_file = "{input_file}"
proxy_mov = "{proxy_mov}"
remove_mov = {remove_mov}
upload_script = "{upload_script}"
print(ver_dict)
print(input_file)
print(proxy_mov)
import os, sys, shutil

sg_module_path = '//192.168.10.190/substorage2/MTHD_core/GlobalLib/Python39'

if not sg_module_path in sys.path:
    sys.path.append(sg_module_path)

import shotgun_api3

sg = shotgun_api3.Shotgun(SG_DOMAIN, session_token=SESSION_TOKEN)\n
"""

        cmd += self.handle_version_creation()
        cmd += self.handle_version_upload()

        cmd += """
try:
    os.remove(upload_script)
    if remove_mov:
        os.remove(proxy_mov)
except Exception as e:
    raise e
"""
        return cmd

    def handle_version_creation(self):
        """Version 생성 로직을 처리하는 스크립트"""
        return """
if 'id' in ver_dict:
    ver_id = ver_dict['id']
else:
    if isinstance(ver_dict['sg_user'], str):
        login = ver_dict['sg_user']
        sg_user = sg.find_one('HumanUser', [['login', 'is', login]])
        if sg_user:
            ver_dict['sg_user'] = sg_user
        else:
            raise 'CANNOT FOUND USER ID IN SHOTGRID'
            
    if 'lev_dict' in ver_dict:
        lev_dict = ver_dict['lev_dict']
        _proj = lev_dict.get('proj')
        _lev0 = lev_dict.get('lev0')
        _lev1 = lev_dict.get('lev1')
        _lev2 = lev_dict.get('lev2')
        _lev3 = lev_dict.get('lev3')
        _lev4 = lev_dict.get('lev4')
        
        # Build filters for the task/entity
        filters = [
            ['project', 'name_is', _proj],
            ['entity', 'name_is', _lev2],
            {
                'filter_operator': 'any',
                'filters': [
                    ['step', 'name_is', _lev3],
                    ['step.Step.short_name', 'is', _lev3],
                ]
            }
        ]
        
        if _lev0:
            if _lev0.lower() in ['asset', 'assets']:
                _lev0 = 'Asset'
                lev1_field = 'sg_asset_type'
            elif _lev0.lower() in ['shot', 'shots']:
                _lev0 = 'Shot'
                lev1_field = 'sg_sequence.Sequence.code'
            else:
                lev1_field = None
            
            filters.insert(1, ['entity', 'type_is', _lev0])
            if lev1_field:
                filters.insert(2, [f'entity.{_lev0}.{lev1_field}', 'is', _lev1])
        
        if _lev4:
            filters.append(['content', 'is', _lev4])
            
        fields = ['project', 'entity', 'content']
        task_entity = sg.find_one('Task', filters, fields)
        
        if task_entity:
            ver_dict['entity'] = task_entity
        else:
            raise ValueError('CANNOT FOUND TASK IN SHOTGRID')

data = {
    'project': ver_dict['entity']['project'],
    'code': ver_dict['name'],
    'description': ver_dict['des'],
    'user': ver_dict['sg_user'],
    'created_by': ver_dict['sg_user'],
    'sg_status_list': ver_dict['status'],
}

if ver_dict['entity']['type'] == 'Task':
    data['entity'] = ver_dict['entity']['entity']
    data['sg_task'] = ver_dict['entity']
else:
    data['entity'] = ver_dict['entity']
    
sg_ver = sg.create('Version', data)
ver_id = sg_ver['id']
"""

    def handle_version_upload(self):
        """Version 업로드 로직을 처리하는 스크립트"""
        return """
try:
    mov_ext = ['MOV', 'MP4', 'AVI', 'WEBM']
    update_info = {
        'sg_uploaded_movie_frame_rate': fps,
        'sg_first_frame': first_frame,
        'sg_last_frame': last_frame
    }
    if input_file.split('.')[-1].upper() in mov_ext:
        update_info['sg_path_to_movie'] = input_file
        sg.upload('Version', ver_id, input_file, 'sg_uploaded_movie')
    else:
        update_info['sg_path_to_frames'] = input_file
        if not remove_mov:
            update_info['sg_path_to_movie'] = proxy_mov
        sg.upload('Version', ver_id, proxy_mov, 'sg_uploaded_movie')
    sg.update('Version', ver_id, update_info)
except:
    sg.delete('Version', ver_id)
    raise
"""

    def _create_deadline_job(self, grp_name, priority, depen_list):
        """Deadline Job 생성"""
        job = {
            'UserName': self.username,
            'Name': f"[{grp_name}] - SG Upload",
            'BatchName': grp_name,
            'Pool': self.pool + '-sg',
            'SecondaryPool': self.sec_pool + '-sg',
            'Priority': priority,
            'Plugin': 'Python',
            'ChunkSize': 1,
            'Frames': 1,
            'ResumeOnCompleteDependencies': True,
            'ResumeOnDeletedDependencies': False,
            'ResumeOnFailedDependencies': False,
        }

        for idx, dep_id in enumerate(depen_list):
            job[f'JobDependency{idx}'] = dep_id

        return job


if __name__ == "__main__":
    test_email = "ttjdwnd77@mortarheadd.co.kr"
    dl = DeadlineManager(test_email)
    