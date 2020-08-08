from functools import wraps

def colorize_closure():
    try:
        import colorama

    except ModuleNotFoundError:
        print("colorama not installed, disabling colored text.")
        return lambda txt, color: str(txt)

    else:
        colorama.init()

        ansi_table = {
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

        def ansi_wrapper(txt, color):
            return ansi_table[color] + str(txt) + ansi_table["END"]

        return ansi_wrapper


colorize = colorize_closure()


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


def bold(txt: str):
    return colorize(txt, 'BOLD')


def header(txt: str):
    return colorize(txt, 'HEADER')


def underline(txt: str):
    return colorize(txt, 'UNDERLINE')


__all__ = ['red', 'green', 'blue', 'cyan', 'purple', 'bold', 'header', 'underline']
