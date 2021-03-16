import logging, sys, os, re, json, subprocess as sp
import vswhere

cache_dir = os.path.expandvars(os.path.join("%LOCALAPPDATA%", "pycmaketools"))
cache_file = os.path.join(cache_dir, "vcvarsall.json")


def load(arch):
    """Get all the relevant env vars directly from vcvarsall.bat

    Parameter
    ---------
    arch : {'x86','amd64','x86_amd64','x86_arm','x86_arm64','amd64_x86','amd64_arm','amd64_arm64'}
        Specify the host and target architectures. Supported arch's may be different for earlier MSVC

    Returns
    -------
    dict or None : Vars if success or None if failed
    """

    # no cache for the given arch found
    msvc = vswhere.find_first(latest=True, products=["*"], prop="installationPath")
    if msvc:
        # run the batch file followed by set to retrieve the modified environmental variables
        vcvarsall = os.path.join(msvc, "VC", "Auxiliary", "Build", "vcvarsall.bat")
        oldpaths = set(os.environ["path"].split(os.pathsep))
        stdout = sp.run(
            f'"{vcvarsall}" {arch} & set',
            capture_output=True,
            encoding="mbcs",
            env=os.environ,
        ).stdout
        logging.debug(stdout)

        # parse the env vars and update the env vars of the current process accordingly
        vars = {}
        for m in re.finditer(
            r"(?<=\n)(include|lib|libpath|path|VSCMD_ARG_HOST_ARCH|VSCMD_ARG_TGT_ARCH)\=(.*?)\n",
            stdout,
            re.IGNORECASE,
        ):
            key = m[1].lower()
            if key == "path":
                vars[key] = os.pathsep.join(
                    tuple(set(m[2].split(os.pathsep)) - oldpaths)
                )
            else:
                vars[key] = m[2]
    
    return vars


def _read_json():
    """Read cached data from JSON file"""
    try:
        with open(cache_file, "rt", encoding="utf-8") as f:
            json_text = f.read()
        json_data = json.loads(json_text)
    except:
        json_data = {}
    return json_data

def clear_cache():
    """Delete the cache data file if exists
    """    
    try:
        os.remove(cache_file)
    except:
        pass


def load_from_cache(arch):
    """Get all the relevant env vars from vcvarsall cache

    Existence of all paths are checked before returning

    Parameter
    ---------
    arch : {'x86','amd64','x86_amd64','x86_arm','x86_arm64','amd64_x86','amd64_arm','amd64_arm64'}
        Specify the host and target architectures. Supported arch's may be different for earlier MSVC

    Returns
    -------
    dict or None : Vars if success or None if failed
    dict : full cache data blob
    """

    # try to load the cached data (empty dict if not avail)
    json_data = _read_json()

    vars = None
    if arch in json_data:
        # validate paths
        _vars = json_data[arch]
        var_iter = (_vars[name] for name in ("include", "lib", "libpath", "path"))
        ok = True
        while var := next(var_iter, False):
            ok = not next(
                (p for p in var.split(os.pathsep) if not os.path.exists(p)), None
            )
        if ok:
            vars = _vars
    return vars, json_data


def save_to_cache(arch, vars, json_data=None):
    """Save the env vars to cache json file

    Parameter
    ---------
    arch : {'x86','amd64','x86_amd64','x86_arm','x86_arm64','amd64_x86','amd64_arm','amd64_arm64'}
        Specify the host and target architectures. Supported arch's may be different for earlier MSVC
    vars : dict
        Env variables for the given arch
    json_data : dict or None
        Full cached data (incl other archs). If not given, read it in from the file

    Returns
    -------
    dict or None : Vars if success or None if failed
    """

    print(f'saved {arch} to cache')

    if not json_data:
        json_data = _read_json()

    # save the variables to json
    json_data[arch] = vars
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    with open(cache_file, "wt", encoding="utf-8") as f:
        f.write(json.dumps(json_data, separators=(",", ":")))


def get_vars(platform=None):
    """Get all the relevant env vars from vcvarsall.bat

    Parameter
    ---------
    platform : {'Win32','x64','ARM','ARM64'} or None, default=None
        Specify target platform if different from the host

    Returns
    -------
    dict or None : Vars if success or None if failed
    """

    # resolve host & target platforms
    host = "amd64" if sys.maxsize > 2 ** 32 else "x86"
    platform_opts = dict(win32="x86", x64="amd64", arm="arm", arm64="arm64")
    arch = host if platform is None else f"{host}_{platform_opts[platform.lower()]}"

    # attempt to get cached
    vars, json_data = load_from_cache(arch)

    if not vars:
        # run vcvarsall
        vars = load(arch)
        if vars:
            # if success, update the cache
            save_to_cache(arch, vars, json_data)

    return vars


def run(platform=None):
    """Launch vcvarsall.bat and update the Python environment

    Parameter
    ---------
    platform : {'Win32','x64','ARM','ARM64'} or None, default=None
        Specify target platform if different from the host

    Returns
    -------
    bool : True if could not run vcvarsall.bat
    """

    if vars := get_vars(platform):

        # parse the env vars and update the env vars of the current process accordingly
        for key, val in vars.items():
            if key == "path":
                ospaths = set(os.environ["path"].split(os.pathsep))
                for newpath in val.split(os.pathsep):
                    ospaths.add(newpath)
                os.environ["path"] = os.pathsep.join(ospaths)
            else:
                os.environ[key] = val

    return vars is None
