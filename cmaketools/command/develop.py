from setuptools.command.develop import develop as _develop_orig
from distutils import log
import setuptools

from .. import cmakeutil
from .. import cmakeoptions


class develop(_develop_orig):

    user_options = [
        ("debug", "g", "compile/link extension modules with debugging information"),
        *_develop_orig.user_options,
        *cmakeoptions.to_distutils("config"),
        *cmakeoptions.to_distutils("build"),
        *cmakeoptions.to_distutils("install"),
    ]

    boolean_options = [
        "debug",
        *_develop_orig.boolean_options,
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
        """adds a mechanism to track/cleanup cmake installed files
        """

        self.get_finalized_command("build_ext", True)
        if self.distribution.has_pure_modules():
            self.get_finalized_command("build_py", True)

        # performed by build_ext command
        build_ext = self.get_finalized_command("build_ext")

        # if uninstalling, remove all extension modules first
        build_ext.develop_pre_run(self.uninstall)

        # run the main routine
        super().run()

        # if installed, copy install_manifest.txt from build dir
        build_ext.develop_post_run(self.uninstall)

    def install_for_development(self):

        self.run_command("egg_info")

        # Build extensions in-place
        self.reinitialize_command("build_ext", inplace=1)
        self.run_command("build_ext")

        if setuptools.bootstrap_install_from:
            self.easy_install(setuptools.bootstrap_install_from)
            setuptools.bootstrap_install_from = None

        self.install_namespaces()

        # create an .egg-link in the installation dir, pointing to our egg
        log.info("Creating %s (link to %s)", self.egg_link, self.egg_base)
        if not self.dry_run:
            with open(self.egg_link, "w") as f:
                f.write(self.egg_path + "\n" + self.setup_path)
        # postprocess the installed distro, fixing up .pth, installing scripts,
        # and handling requirements
        self.process_distribution(None, self.dist, not self.no_deps)
