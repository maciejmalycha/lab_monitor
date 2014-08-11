# usage: from config import config

import yaml
import os

src_dir = os.path.dirname(os.path.realpath(__file__))
cfile = os.path.join(src_dir, '..', 'config.yaml')

with open(cfile) as cf:
    config = yaml.load(cf)
