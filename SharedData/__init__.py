from os import chdir, path
from sys import argv
from urllib import request
from types import SimpleNamespace
from .ColorSupport import *
import json
import pkgutil


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
    req = request.urlopen("https://api.ipify.org")
    data = req.read()
    return data.decode("utf-8")


def load_config_new(json_file=None):
    data = load_config_json(json_file)

    return SimpleNamespace(**data)


def load_config_json(json_file=None):
    if json_file:
        source = json_file
    else:
        source = pkgutil.get_data(__package__, 'config.json')
    data = json.loads(pkgutil.get_data(__package__, 'config.json'))
    data['END_MARK'] = data['END_MARK'].encode(data['ENCODING'])

    if data['INIT_PORT'] not in data['EXCLUDE']:
        data['EXCLUDE'].append(data['INIT_PORT'])

    return data


# closure. Yield function that convert int to bytes, stores given parameters.
def rw_bytes(byte_size: int, byte_order: str, eof: bytes, encoding: str):

    def write_as_byte(n: int) -> bytes:
        # assume n is int. If not, as a debugging feature, check if data is
        # already bytes. Send if so, raise error back otherwise.
        try:
            return n.to_bytes(byte_size, byte_order)
        except AttributeError:
            if isinstance(n, bytes):
                return n

            raise

    def read_from_byte(b: bytes):
        # if eof then convert to str. Waste of processing power.
        if b == eof:
            return b

        return int.from_bytes(b, byte_order)

    return read_from_byte, write_as_byte


def alive_thread_gen(lst: list):
    for idx, t in enumerate(lst):
        yield t.is_alive()


def any_thread_alive(lst: list):  # list containing threads.
    return any(alive_thread_gen(lst))
