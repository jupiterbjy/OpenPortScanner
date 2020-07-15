from os import chdir, path
from sys import argv
from urllib import request
from types import SimpleNamespace
import json

try:
    import colorama
except ModuleNotFoundError:
    COLOR = False
else:
    colorama.init()
    COLOR = True


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


# assuming file is placed in same structure.
def load_config():
    with open(loc + "/config.json") as f:
        data = json.load(f)
        return SimpleNamespace(**data)


# just a convenient method
def prepare(file):
    set_working_dir(file)
    return load_config()


# closure. Yield function that convert int to bytes, stores given parameters.
def rw_bytes(byte_size, byte_order, eof, encoding):
    size = byte_size
    order = byte_order

    def write_as_byte(n: int) -> bytes:
        return n.to_bytes(size, order)

    def read_from_byte(b: bytes):  # if eof then convert to str.
        if b == eof:
            return b.decode(encoding)
        return int.from_bytes(b, order)

    return read_from_byte, write_as_byte


def alive_thread_gen(lst: list):
    for idx, t in enumerate(lst):
        yield t.is_alive()


def any_thread_alive(lst: list):  # list containing threads.
    if any(alive_thread_gen(lst)):
        return True

    return False


def Colorize(txt, color):
    if not COLOR:
        return txt

    ansi = {
        "RED": "\033[91m",
        "GREEN": "\033[92m",
        "BLUE": "\033[94m",
        "YELLOW": "\033[93m",
        "PURPLE": "\033[94m",
        "CYAN": "\033[96m",
        "END": "\033[0m",
        "BOLD": "\033[1m",
        "HEADER": "\033[95m",
        "UNDERLINE": "\033[4m",
    }
    s = str(txt)
    return ansi[color] + s + ansi["END"]
