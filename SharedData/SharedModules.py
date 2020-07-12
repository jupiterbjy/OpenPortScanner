from os import chdir, path
from sys import argv
from urllib import request
from types import SimpleNamespace
import json


loc = path.dirname(path.abspath(__file__))


def set_working_dir(file=__file__):
    if file:
        try:
            chdir(path.dirname(path.abspath(file)))
        except FileNotFoundError:  # linux, for some reason
            pass
    else:
        chdir(path.dirname(argv[0]))


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


# assuming file is placed in same structure.
def load_config():
    with open(loc + '/config.json') as f:
        data = json.load(f)
        return SimpleNamespace(**data)


# just a convenient method
def prepare(file):
    set_working_dir(file)
    return load_config()


# closure. Yield function that convert int to bytes, stores given parameters.
def rw_bytes(byte_size, byte_order):
    size = byte_size
    order = byte_order

    def write_as_byte(n: int) -> bytes:
        return n.to_bytes(size, order)

    def read_from_byte(b: bytes) -> int:
        return int.from_bytes(b, order)

    return read_from_byte, write_as_byte
