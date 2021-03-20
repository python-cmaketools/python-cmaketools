import re
import subprocess as sp
import os
import logging
from shutil import which

gitmodules_status_filename = ".gitmodules_status"


def find_git(cmd=None):
    """Find full path to the git binary

    Returns:
        str: Path to git executable
    """
    return which(cmd or "git")


def read_config(path):
    """Read git config files

    Args:
        path (str): Path to the config file

    Returns:
        dict: multi-level dict. Top-level keys are the subsection and variables of the sections
              Subsections values are dicts, listing subsection variables.

    Known Issue: Name collision could happen if section variable and subsection have the same name.
                 Currently, this is not an issue as only .gitmodules are processed.
    """
    with open(path, "r") as f:
        txt = f.read()

    txt = re.sub(r"\s*[#;].*?(?=\n)", "", txt)  # remove comments
    txt = re.sub(r"^$\n", "", txt, flags=re.MULTILINE)  # remove empty lines

    # find sections
    s = None
    mline = False
    sec = None
    data = {}
    for m in re.finditer(r"^\s*(.+)(\s*\\\s*)?", txt, flags=re.MULTILINE):
        if mline:
            s += " " + m[1]
        else:
            s = m[1]

        mline = m[2]
        if mline:
            continue

        if s[0] == "[":
            # section def
            m = re.search(r'^\[([a-zA-Z0-9\-]+)(?:\s*\s"(.+?(?<!\\))")?\]', s)
            if m[1] not in data:
                sec = data[m[1]] = {}
            if m[2] and m[2] not in sec[m[2]]:
                sec = sec[m[2]] = {}

        else:
            # var def
            m = re.search(r"^([a-zA-Z][a-zA-Z-0-9\-]*)(?:\s*=\s*(.+))?", s)
            sec[m[1]] = m[2]

    return data


def has_submodules():
    """True if project uses git submodules

    Returns:
        bool: True if current working directory has '.gitmodule' file
    """
    return os.path.isfile(".gitmodules")


def list_submodules():
    try:
        return read_config(".gitmodules")["submodule"]
    except:
        return None


def save_gitmodules(dst_dir=".", excludes=None):
    """Save git submodule status

    Args:
        dst_dir (str, optional): To save the status file (.gitmodules_status) to this directory. Defaults to ".".
        excludes (seq<str>, options): list of submodule paths to exclude in status

    Returns
    -------
        bool : True if saved
    """

    # get reducted 'git submodule status' text
    gitmodules_status = capture_submodule_status(excludes)

    if gitmodules_status:
        # save the text as .gitmodules_status file in the specified folder
        with open(os.path.join(dst_dir, gitmodules_status_filename), "wt") as f:
            f.write(gitmodules_status)

    return bool(gitmodules_status)


def delete_gitmodules(dir="."):
    os.remove(os.path.join(dir, gitmodules_status_filename))


def load_gitmodules(src_dir="."):
    """Load git submodule status

    If .gitmodules_status is not found, no action is taken

    Args:
        src_dir (str, optional): Load status file (.gitmodules_status) from this directory. Defaults to ".".
        excludes (tuple, optional): If any submodules are not needed, add its location within the project this tuple. Defaults to ().

    Returns
    -------
        str or None: The text content of .gitmodules_status file. None if the file is not found in the specified folder.
    """

    try:
        with open(os.path.join(src_dir, gitmodules_status_filename), "rt") as f:
            gitmodules_status = f.read()
    except:
        gitmodules_status = None

    return gitmodules_status


def capture_submodule_status(excludes=None):
    """Capture git submodule status output

    Returns the output of 'git submodule status' command

    Args:
        excludes (seq<str>, options): list of submodule paths to exclude in status

    Returns
    -------
    str or None : submodule status output or None if no submodules used
    """

    output = (
        sp.run(
            (
                "git",
                "submodule",
            ),
            capture_output=True,
            universal_newlines=True,
        ).stdout
        if has_submodules()
        else None
    )

    # filter if excludes specified
    if output:
        output = "\n".join(
            [
                m[1] + " " + m[2]
                for m in re.finditer(
                    r"([\-+][0-9a-f]+)\s(.+?)\s(\(.+?\))?\n", output, flags=re.MULTILINE
                )
                if not (excludes and m[2] in excludes)
            ]
        )
    return output


def clone_submodules():
    """Clone submodules

    This function is designed to be used when the project is built from sdist tarball.
    Because the tarball does not retain the git repo of the project, each submodule
    must be cloned independently according to the included .gitmodules_status file,
    which contains the capture of git submodule status at the time of tarball creation.

    """

    # get pinned submodule info (.submodule_status file)
    status = load_gitmodules()

    # work only if project contains does not use any submodule, nothing to do
    if status:
        # get submodule configurations (must exist)
        config = read_config(".gitmodules")["submodule"]

        # if .gitmodules_status is provided, get sha1 hash keys
        for m in re.findall(r".([0-9a-f]{5,40})\s(.+)", status):
            sha1 = m[1]
            path = m[2]
            url = config[path]["url"]

            logging.info(f"[git] cloning {url} to {path}...")
            clone(url, path, sha1)

        logging.info("[git] cloning complete.")


def clone(repository, directory, branch):
    """Run git clone command

    Args:
        repository (str): Source URL of the repository
        directory (str): Destination relative location of the repo
        branch (str): branch name or SHA1 of the commit
    """
    sp.run(
        ["git", "clone", "-b", branch, repository, "--recurse-submodules", directory]
    )
