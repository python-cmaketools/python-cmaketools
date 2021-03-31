from setuptools.command.develop import develop as _develop_orig


class develop(_develop_orig):

    user_options = _develop_orig.user_options + [
        ("debug", "g", "compile/link extension modules with debugging information"),
    ]

    boolean_options = _develop_orig.boolean_options + ["debug"]

    def initialize_options(self):
        self.debug = None
        return super().initialize_options()

    def run(self):
        """adds a mechanism to track/cleanup cmake installed files
        """

        # performed by build_ext command
        build_ext = self.get_finalized_command("build_ext")

        # if uninstalling, remove all extension modules first
        build_ext.develop_pre_run(self.uninstall)

        # run the main routine
        super().run()

        # if installed, copy install_manifest.txt from build dir
        build_ext.develop_post_run(self.uninstall)
