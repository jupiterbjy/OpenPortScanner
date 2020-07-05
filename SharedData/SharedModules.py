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


# closure. Yield function that convert int to bytes, stores given parameters.
def to_byte(byte_size, byte_order):
    size = byte_size
    order = byte_order

    def write_as_byte(n: int) -> bytes:
        return n.to_bytes(size, order)

    def read_from_byte(b: bytes) -> int:
        return int.from_bytes(b, order)

    return read_from_byte, write_as_byte
