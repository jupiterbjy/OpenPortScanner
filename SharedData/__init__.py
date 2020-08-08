from os import chdir, path
from sys import argv
from urllib import request
from types import SimpleNamespace
import json
import pkgutil

try:
    import colorama
except ModuleNotFoundError:
    print("colorama not installed, disabling colored text.")
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


def load_config_new():
    data = json.loads(pkgutil.get_data(__package__, 'config.json'))
    return SimpleNamespace(**data)


# closure. Yield function that convert int to bytes, stores given parameters.
def rw_bytes(byte_size: int, byte_order: str, eof: str, encoding: str):

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
        if b == eof.encode(encoding=encoding):
            return b.decode(encoding)

        return int.from_bytes(b, byte_order)

    return read_from_byte, write_as_byte


def alive_thread_gen(lst: list):
    for idx, t in enumerate(lst):
        yield t.is_alive()


def any_thread_alive(lst: list):  # list containing threads.
    return any(alive_thread_gen(lst))


def colorize(txt, color):
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


# anti lambda?
def red(txt: str):
    return colorize(txt, 'RED')


def green(txt: str):
    return colorize(txt, 'GREEN')


def blue(txt: str):
    return colorize(txt, 'BLUE')


def cyan(txt: str):
    return colorize(txt, 'CYAN')


def purple(txt: str):
    return colorize(txt, 'PURPLE')
