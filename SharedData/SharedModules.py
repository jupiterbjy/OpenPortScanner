from os import chdir, path
from sys import argv
from urllib import request
from socket import socket
from types import SimpleNamespace
import json


loc = path.dirname(__file__)


def set_working_dir(file=None):
    if file:
        chdir(path.dirname(file))
    else:
        chdir(path.dirname(argv[0]))


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


# assuming file is placed in same structure.
def load_config():
    with open(loc + '\\config.json') as f:
        data = json.load(f)
        return SimpleNamespace(**data)


# just a convenient method
def prepare(file):
    set_working_dir(file)
    return load_config()


def read_until(sock: socket, end: str):
    while True:
        pass
