from os import path, listdir, chdir, mkdir
from shutil import move, copy
import time
import re


TIME_MODIFIER = 0.5


# some idiotic algorithm to find if there is common prefix in file naming.
def reducing_gen(s: str):
    # remove file type annotation to argument!
    s = s.rstrip(".abc")

    for block in s.split():
        # we're grouping same prefix, so it's ok to discard last element on Start.
        s = s.rstrip(block)
        if s:
            yield s

    # split = re.split(r'\W+', s)
    #
    # for block in reversed(split):
    #     # we're grouping same prefix, so it's ok to discard last element on Start.
    #     if s.endswith(('-', ' ', '_')):
    #         s = s[:-1].rstrip(' ' + block)
    #     else:
    #         s = s.rstrip(block)
    #
    #     if s:
    #         yield s


def fancy_delay(loc):
    group = [i for i in listdir(path.abspath(loc)) if i.endswith(".abc")]
    # what normal pep (me before) does:
    # return group

    # what I do instead
    max_digit = len(str(len(group)))

    for idx, i in enumerate(group):
        print(f"[{idx + 1:^{max_digit}}/{len(group)}] {i}", end="")
        time.sleep(TIME_MODIFIER / len(group))  # just to make things fancy
        print("\b" * len(i), end="\r")

        # could use contextmanager for this, maybe.

    return group


def strip_hyphen(lst: list):
    # just trying strip to all element is simplest, i guess.
    return [i.rstrip("- ") for i in lst]


def find_file_prefixes(files: list):
    files_copy = list(files)
    files_captured = set()
    group = []

    for file in files_copy:
        if file in files_captured:
            continue

        file: str
        print(f"Finding prefix for {file}", end="")

        for template_prefixes in reducing_gen(file):
            # triple loop, lel
            output = set(i for i in files_copy if i.startswith(template_prefixes))

            if len(output) > 1:
                group.append(template_prefixes)
                files_captured = files_captured | output
                break

        time.sleep(TIME_MODIFIER / len(files_copy))  # just to make things fancy
        print("\b" * len(file), end="\r")

    return strip_hyphen(group)


def group_in_folders(prefixes: list, files: list):
    print("Backing up files to 'assets/user/abc_backup'")
    try:
        mkdir(r"..\abc_backup")
    except FileExistsError:
        pass

    print("Generating prefix folders")
    gen_folders(prefixes)

    for p in prefixes:
        for f in files:
            if f.startswith(p):
                print(f"Moving, renaming, backing up File {f}")
                # backup
                try:
                    copy(path.abspath(f), "../abc_backup/" + f)
                except FileExistsError:
                    pass
                except FileNotFoundError:
                    pass  # how this is even possible? but it's happening.

                # moving to prefix folder
                f: str
                try:
                    move(f, f"{p}//{f.lstrip(p)}")
                except FileNotFoundError:
                    print(f"Error on file {f}")


def gen_folders(lst: list):

    for i in lst:
        try:
            mkdir(i)
        except FileExistsError:
            pass


def main():
    # loc = input("abc Folder location: ")
    loc = r"Z:\Steam\steamapps\common\Starbound\assets\user\songs"
    # loc = r"user\songs"
    try:
        chdir(loc)
    except FileNotFoundError:
        print("No such directory.")
        return

    abc_outside_folder = fancy_delay(loc)
    print(f"Found {len(abc_outside_folder)} not organized files.")

    if pref_group := find_file_prefixes(abc_outside_folder):  # python 3.8
        print(f"Now will be organising Following prefixes: \n{pref_group}")
        # group_in_folders(pref_group, abc_outside_folder)
    else:
        print("No suitable prefix pattern found.")


main()
