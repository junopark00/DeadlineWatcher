# -*- coding: utf-8 -*-

import os
import glob

def get_latest_rv_path():
    base_dir = r"C:\Program Files\ShotGrid"
    if not os.path.exists(base_dir):
        return None

    rv_paths = glob.glob(os.path.join(base_dir, "RV-*", "bin", "rv.exe"))
    if not rv_paths:
        return None

    def extract_version(path):
        import re
        match = re.search(r"RV-(\d+(?:\.\d+)*)", path)
        return tuple(map(int, match.group(1).split("."))) if match else (0,)

    rv_paths.sort(key=extract_version, reverse=True)
    return rv_paths[0] if rv_paths else None
