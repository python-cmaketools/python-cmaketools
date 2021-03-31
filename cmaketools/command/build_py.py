from setuptools.command.build_py import build_py as _build_py_orig


class build_py(_build_py_orig):
    user_options = [
        ("use-cmake", None, "use CMake's PY install COMPONENT to perform the build",),
        ("use-setuptools", None, "do not use CMake's PY install COMPONENT to perform the build",)
    ] + _build_py_orig.user_options
    boolean_options = ["use-cmake",] + _build_py_orig.boolean_options
    negative_opt = {
        "use-setuptools": "use-cmake",
        **_build_py_orig.negative_opt,
    }

    def __init__(self, dist):
        self.use_cmake = None
        self.cmake_job = None
        return super().__init__(dist)

    def initialize_options(self):
        self.use_cmake = None
        return super().initialize_options()

    def ensure_cmake_started(self):

        if self.use_cmake and not self.cmake_job:
            self.cmake_job = self.distribution.cmake.install(
                prefix=self.dist_dir,
                component="PY",
                pkg_version=self.distribution.get_version(),
            )

    def run(self):

        if self.use_cmake:
            self.ensure_cmake_started()
            self.distribution.camke.wait(self.cmake_job)
        else:
            _build_py_orig.run(self)

