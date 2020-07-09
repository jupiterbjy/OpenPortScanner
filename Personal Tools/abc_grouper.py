from os import path, listdir, chdir, mkdir
from shutil import move
import time


# some idiotic algorithm to find if there is common prefix in file naming.
def reducing_gen(s: str):
    # remove file type annotation to argument!
    for block in s.split():
        # we're grouping same prefix, so it's ok to discard last element on Start.
        s = s.rstrip(block)
        if s:
            yield s


def fancy_delay(loc):
    group = [i for i in listdir(path.abspath(loc)) if i.endswith(".abc")]

    # what normal pep (me before) does:
    # return group

    # what I do instead
    max_digit = len(str(len(group)))

    for idx, i in enumerate(group):
        time.sleep(0.05)  # just to make things fancy
        print(f"[{idx + 1:^{max_digit}}/{len(group)}] {i}", end='\r')

    return group


def strip_hyphen(lst: list):
    # just trying strip to all element is simplest, i guess.
    return [i.rstrip('- ') for i in lst]


def find_file_prefixes(files: list):
    files_copy = list(files)
    files_captured = set()
    group = []

    for file in files_copy:
        if file in files_captured:
            continue

        file: str
        time.sleep(0.05)  # just to make things fancy
        print(f"Finding prefix for {file}", end="\r")

        for template_prefixes in reducing_gen(file):
            # triple loop, lel
            output = set(i for i in files_copy if i.startswith(template_prefixes))
            if len(output) > 1:
                group.append(template_prefixes)
                files_captured = files_captured | output
                break

    return strip_hyphen(group)


def group_in_folders(prefixes: list, files: list):
    gen_folders(prefixes)
    for f in files:
        for p in prefixes:
            if f.startswith(p):
                move(f, f"{p}/{f}")


def gen_folders(lst: list):
    for i in lst:
        try:
            mkdir(i)
        except FileExistsError:
            pass


def main():
    loc = input("abc Folder location: ")
    # loc = r"Z:\Steam\steamapps\common\Starbound\assets\user\songs"
    chdir(loc)

    abc_outside_folder = fancy_delay(loc)
    print(f"Found {len(abc_outside_folder)} not organized files.")

    pref_group = find_file_prefixes(abc_outside_folder)
    max_digit = len(str(len(pref_group)))  # this looks funny, but fast.

    print(f"Now will be organising Following prefixes:")
    print(pref_group)

    group_in_folders(pref_group, abc_outside_folder)


main()
