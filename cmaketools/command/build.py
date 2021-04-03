"""cmaketools.command.build

Implements the cmaketools 'build' command.

based on Distutils.command.build.
"""

from distutils.command.build import build as _orig_build
from .. import cmakeutil
from .. import cmakeoptions


class build(_orig_build):

    user_options = [
        *[
            opt
            for opt in _orig_build.user_options
            if opt[0] not in ("build-temp", "plat-name", "compiler", "parallel")
        ],
        *cmakeoptions.to_distutils("config"),
        *cmakeoptions.to_distutils("build"),
        *cmakeoptions.to_distutils("install"),
    ]

    boolean_options = [
        *_orig_build.boolean_options,
        *cmakeoptions.to_distutils_bools("config"),
        *cmakeoptions.to_distutils_bools("build"),
        *cmakeoptions.to_distutils_bools("install"),
    ]

    help_options = [
        ("help-compiler", None, "list available compilers", cmakeutil.show_generators),
    ]

    def initialize_options(self):
        super().initialize_options()
        for o in cmakeoptions.config_options.keys():
            setattr(self, o, None)

        for o in cmakeoptions.build_options.keys():
            setattr(self, o, None)

        for o in cmakeoptions.install_options.keys():
            setattr(self, o, None)

    def run(self):
        # finalize options of both build_py & build_ext first to initiate cmake build process
        if self.has_pure_modules():
            build_py = self.get_finalized_command("build_py")
            build_py.ensure_cmake_started()
        if self.has_ext_modules():
            build_ext = self.get_finalized_command("build_ext")
            build_ext.ensure_cmake_started()

        # then run the sub commands to retrieve the cmake outcomes
        super().run()

    sub_commands = [cmd for cmd in _orig_build.sub_commands if cmd[0] != "build_clib"]

