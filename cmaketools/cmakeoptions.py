"""Defines non-Python critical CMake options
"""

from os import pathsep as sep_by
from distutils.errors import DistutilsOptionError
import re

sep_by_txt = f" (separated by '{sep_by}')"


def reformat_config(opt, val):
    return f"-DCMAKE_BUILD_TYPE:STRING={val}"


def reformat_define(D, defines):
    """generate CMake -D options string

    if defines is a str, it first gets split at ';'
    if defines is a sequence of str, it is tested for '<var>:<value>' or '<var>:<type>:<value>'
    patterns
    if defines is a sequence of sequence of str, each element of the inner sequence is
    either [<var>,<value>] or [<var>,<type>,<value>]

    Args:
        opt (str): should be "-D"
        defines (str or seq of str or seq of seq of str): [description]

    Raises:
        DistutilsOptionError: [description]

    Returns:
        [type]: [description]
    """

    if isinstance(defines, str):
        defines = defines.split(sep_by)

    def regen_d(dstr):
        if isinstance(dstr, str):
            m = re.match(r"([^:=\n]+)(?:\:([^:\n]+))?[:=]([^\n]+)$", dstr)
            if not m:
                raise DistutilsOptionError(
                    f"Invalid `defines` (-D in cmake) option: {dstr}"
                )
        if re.search(r"\s", m[3]):
            m[3] = f'"{m[3]}"'
        return f"-D{m[1]}:{m[2]}={m[3]}" if m[2] else f"-D{m[1]}={m[3]}"

    return " ".join([regen_d(d) for d in defines])


def reformat_undefine(opt, vals):
    """generate CMake -U options

    Args:
        opt (str): option name (-U)
        vals (str or seq of str): ';' separated list or a ready-to-go sequence

    Returns:
        str: space separated argument - -U var1 -u var2 ...
    """
    if vals and isinstance(vals, str):
        vals = vals.split(sep_by)
    return " ".join([f"{opt} {val}" for val in vals])


# fmt: off
config_options = dict(
cache=('-C',' ',"Pre-load a CMake script to populate the cache."),
generator=('-G',' ',"Specify a build system generator."),
toolset=('-T',' ',"Toolset specification for the generator, if supported."),
platform=('-A',' ',"Specify platform name if supported by generator."),
config=("--config",reformat_config,"CMAKE_BUILD_TYPE: Debug, Release, RelWithDebInfo, or MinSizeRel."),
defines=('-D',reformat_define, "List of CMake CACHE entries: name=value or name:type=value" + sep_by_txt),
undefs=('-U',reformat_undefine, "List of entries to remove from CMake CACHE." + sep_by_txt),
Wno_dev=('-Wno-dev',None,"Suppress developer warnings."),
Wdev=("-Wdev",None,"Enable developer warnings."),
Werror=("-Werror","=","Make specified warnings into errors: dev or deprecated."),
Wno_error=("-Wno-error","=","Make specified warnings not errors."),
Wdeprecated=("-Wdeprecated",None,"Enable deprecated functionality warnings."),
Wno_deprecated=("-Wno-deprecated",None,"Suppress deprecated functionality warnings."),
log_level=("--log-level","=","Set the log level to one of: ERROR, WARNING, NOTICE, STATUS, VERBOSE, DEBUG, TRACE"),
log_context=("--log-context",None,"Enable the message() command outputting context attached to each message."),
debug_trycompile=("--debug-trycompile",None,"Do not delete the try_compile() build tree. Only useful on one try_compile() at a time."),
debug_output=("--debug-output",None,"Put CMake in a debug mode."),
debug_find=("--debug-find",None,"Put CMake find commands in a debug mode."),
trace=("--trace",None,"Put cmake in trace mode."),
trace_expand=("--trace-expand",None,"Put cmake in trace mode with variables expanded."),
trace_format=("--trace-format","=","Put cmake in trace mode and sets the trace output format."),
trace_source=("--trace-source","=","Put cmake in trace mode, but output only lines of a specified file."),
trace_redirect=("--trace-redirect","=","Put cmake in trace mode and redirect trace output to a file instead of stderr."),
warn_uninitialized=("--warn-uninitialized",None,"Specify a build system generator."),
warn_unused_vars=("--warn-unused-vars",None,"Warn about unused variables."),
no_warn_unused_cli=("--no-warn-unused-cli",None,"Don’t warn about command line options."),
check_system_vars=("--check-system-vars",None,"Find problems with variable usage in system files."),
profiling_output=("--profiling-output","=","Used in conjunction with --profiling-format to output to a given path."),
profiling_format=("--profiling-format","=","Enable the output of profiling data of CMake script in the given format."),
preset=("--preset","=","Reads a preset from <path-to-source>/CMakePresets.json and <path-to-source>/CMakeUserPresets.json."),
)

build_options=dict(
parallel=("-j"," ","The maximum number of concurrent processes to use when building."),
clean_first=("--clean-first",None,"Build target clean first, then build."),
verbose=("-v",None,"Enable verbose output - if supported - including the build commands to be executed."),
native=("--"," ","Pass as the option string to the native tool.")
)

install_options=dict(
strip=("--strip",None,"Strip before installing."),
verbose=("-v",None,"Enable verbose output."),
default_directory_permissions=("--default-directory-permissions"," ", "Default directory install permissions. Permissions in format <u=rwx,g=rx,o=rx>.")
)
# fmt: on

option_dict = dict(config=config_options, build=build_options, install=install_options)


def to_distutils(type):
    """convert given cmake option to distutils user_options"""

    def convert(key, opt):
        suffix = "" if opt[1] is None else "="
        return (
            (opt[0][2:] + suffix, None, opt[2])
            if opt[0].startswith("--") and len(opt[0])>2
            else (opt[0][1:] + suffix, None, opt[2])
            if len(opt[0]) > 2
            else (key + suffix, opt[0][1], opt[2])
        )

    return tuple((convert(key, opt) for key, opt in option_dict[type].items()))


def to_distutils_bools(type):
    """convert given cmake option to distutils boolean_options"""

    return tuple(
        (
            opt[0][2:]
            if opt[0].startswith("--")
            else opt[0][1:]
            if len(opt[0]) > 2
            else key.replace("_", "-")
            for key, opt in option_dict[type].items()
            if opt[1] is None
        )
    )


def generate_arg_for(type, src):
    """Generate CMake option argument from camketools command object

    Args:
        type (str): specify the type of cmake call: 'config', 'build', or 'install'
        src (cmaketools.Command): command object to retrieve option values from

    Returns:
        str: ready-to-append option arguments
    """

    options = option_dict[type]

    def process_this(type, o):
        val = getattr(src, type)
        opt = o[0]
        sep = o[1]
        if sep == None and val:
            return opt
        else:
            if re.search(r"\s", val):
                val = f'"{val}"'
            return f"{opt}{sep}{val}" if isinstance(sep, str) else sep(opt, val)

    return " ".join(
        [
            process_this(type, value)
            for type, value in options.items()
            if getattr(src, type, None) is not None
        ]
    )
