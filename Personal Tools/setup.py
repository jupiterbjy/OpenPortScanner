from cx_Freeze import setup, Executable
import sys

version = "0.0.6"

build_options = {
    "packages": [],
    "excludes": [],
    "build_exe": "X:\\builds\\",
}

executables = [Executable("abc_grouper.py", targetName="abc_grouper")]

setup(
    name="abc_grouper",
    options={"build_exe": build_options},
    executables=executables,
)
