import re
import configparser as cp
import subprocess as sp
import os
import posixpath
import pathlib

gitmodules_status_name = ".gitmodules_status"


def has_submodules():
    return os.path.isfile(".gitmodules")


def save_submodule_status(dst_dir="dist"):
    """Save the current submodule status in a '.submodule_status' file in dst_dir"""
    # if project does not use any submodule, nothing to do
    if not has_submodules():
        return []

    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    out = sp.run(("git", "submodule",), capture_output=True, text=True)
    file = posixpath.join(dst_dir, gitmodules_status_name)
    with open(file, "w") as f:
        f.write(out.stdout)
    return file


def clone_submodules(status_dir="dist", excludes=[]):
    """Clone submodules if missing

    """

    # if project does not use any submodule, nothing to do
    if not has_submodules():
        return

    print("[git] .gitmodules found. Cloning the submodules if necessary")

    # parse .submodule for submodule paths
    parser = cp.ConfigParser(delimiters="=")
    parser.read(".gitmodules")
    submodules = [
        dict(src=module["url"], dst=module["path"], sha1=None)
        for (name, module) in parser.items()
        if name is not "DEFAULT"
    ]

    # if .gitmodules_status is provided, get sha1 hash keys
    status_path = os.path.join(status_dir, gitmodules_status_name)
    if os.path.isfile(status_path):
        with open(status_path, "r") as f:
            status = f.read()
        for m in re.findall(r".([0-9a-f]{5,40})\s(.+)\s\(.*?\)", status):
            next(module for module in submodules if m[1] == module["dst"])["sha1"] = m[
                0
            ]

    # clone only if dst does not exist then checkout specific branch/tag if sha1 is given
    for module in submodules:
        # skip modules in excludes argument
        if module["dst"] in excludes:
            continue

        if os.path.exists(os.path.join(module["dst"], ".git")):
            msg = f'[git] submodule {module["dst"]} is already present.'
        else:
            print(f'[git] cloning {module["src"]} to {module["dst"]}...')
            clone(module["src"], module["dst"])
            msg = "[git] cloning complete."

        if module["sha1"] and module["sha1"] != get_sha1(module["dst"]):
            print(msg + " Checking out the specified commit...")
            checkout(module["dst"], module["sha1"])
        else:
            print(msg)


def get_sha1(submodule):
    return rev_parse(submodule, "HEAD")


def clone(repository, directory, **kw):
    args = ["git", "clone", repository, directory]
    if not "recurse_submodules" in kw or kw["recurse_submodules"]:
        args.append("--recurse-submodules")
    sp.run(args)


def checkout(directory, branch):
    sp.run(("git", "checkout", branch,), cwd=directory)


def rev_parse(directory, *args):
    return sp.run(
        ("git", "rev-parse",) + args, cwd=directory, text=True, capture_output=True
    ).stdout
