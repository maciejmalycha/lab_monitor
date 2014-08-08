# usage: from config import config

import yaml
with open('../config.yaml') as cf:
    config = yaml.load(cf)