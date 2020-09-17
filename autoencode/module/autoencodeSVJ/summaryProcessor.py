import autoencode.module.autoencodeSVJ.utils as utils

import os
import json
import glob
import datetime
import pandas as pd

from pathlib import Path
from collections import OrderedDict


def dump_summary_json(*dicts, output_path):
    summary = OrderedDict()
    
    for d in dicts:
        summary.update(d)
    
    assert 'filename' in summary, 'NEED to include a filename arg, so we can save the dict!'
    
    fpath = os.path.join(output_path, summary['filename'] + '.summary')
    
    if os.path.exists(fpath):
        newpath = fpath
        
        while os.path.exists(newpath):
            newpath = fpath.replace(".summary", "_1.summary")
        
        # just a check
        assert not os.path.exists(newpath)
        fpath = newpath
    
    summary['summary_path'] = fpath
    
    with open(fpath, "w+") as f:
        json.dump(summary, f)
    
    return summary


def summary_vid(path=""):
    Path(path).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(path, "VID")
    
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            vid = int(file.read().strip('\n').strip())
            return vid
    else:
        file = open(filepath, "w")
        file.write("0\n")
        return 0


def summary_by_name(name):
    if not name.endswith(".summary"):
        name += ".summary"
    
    if os.path.exists(name):
        return name
    
    matches = summary_match(name)
    
    if len(matches) == 0:
        raise AttributeError
    elif len(matches) > 1:
        raise AttributeError
    
    return matches[0]


def load_summary(path):
    assert os.path.exists(path)
    with open(path, 'r') as f:
        ret = json.load(f)
    return ret


def summary(custom_dir,
            include_outdated=False,
            defaults={'hlf_to_drop': ['Flavor', 'Energy']}
            ):
    files = glob.glob(os.path.join(custom_dir, "*.summary"))
    
    print("Opening summary files: ", files)
    
    data = []
    for f in files:
        with open(f) as to_read:
            d = json.load(to_read)
            d['time'] = datetime.datetime.fromtimestamp(os.path.getmtime(f))
            for k, v in list(defaults.items()):
                if k not in d:
                    d[k] = v
            data.append(d)
    
    s = utils.data_table(pd.DataFrame(data), name='summary')
    # if 'hlf_to_drop' in s:
    #     s.hlf_to_drop.fillna(('Energy', 'Flavor'), inplace=True)
    if include_outdated:
        return s
    return utils.data_table(s[s.VID == s.VID.max()], name='summary')


def summary_match(search_path, verbose=True):
    ret = glob.glob(search_path)
    if verbose:
        print("Summary matches search_path: ", search_path, "\tglob path: ", ret)
        print(("found {} matches with search '{}'".format(len(ret), search_path)))
    return ret


def summary_by_features(**kwargs):
    data = summary(include_outdated=True)
    
    for k in kwargs:
        if k in data:
            data = data[data[k] == kwargs[k]]
    
    return data
