from setuptools.command.sdist import sdist as _sdist_orig
from setuptools.dist import DistutilsOptionError, DistutilsSetupError
from .. import gitutil, cmakeutil
import os, shutil, contextlib

class sdist(_sdist_orig):
    """Prepares MANIFEST.in before running the original sdist to include
    all the files in the source folder
    """

    sep_by = " (separated by '%s')" % os.pathsep

    user_options = [
        ("include-gitmodules", None, "include git submodules to tarball"),
        (
            "nondist-gitmodules=",
            None,
            "List of git submodules not used for building" + sep_by,
        ),
        (
            "nondist-dirs=",
            None,
            "List of dirs with CMakeLists.txt which are not used for building" + sep_by,
        ),
    ] + _sdist_orig.user_options

    boolean_options = ["include-gitmodules"] + _sdist_orig.boolean_options

    def __init__(self, dist):
        super().__init__(dist)

    def initialize_options(self):
        self.auto_manifest = None
        self.include_gitmodules = None
        self.nondist_gitmodules = None
        self.nondist_dirs = None
        self.manifest_modified = False
        return super().initialize_options()

    def run(self):
        """Create the source distribution(s). The list of archive files created is
        stored so it can be retrieved later by 'get_archive_files()'.

        Before creating the distributions, pin git submodule commit so installing
        from sdist at any point in the future will use the same commit
        """

        # https://packaging.python.org/guides/using-manifest-in/

        work_dir = os.path.join(
            self.get_finalized_command("build").build_base, "cmaketools_sdist"
        )
        os.makedirs(work_dir, exist_ok=True)

        # prepare self.cmake_manifest with commands to copy cmake folders
        # also get a list of pruned directories (by exclude_dirs)
        pruned_dirs = self._create_cmake_manifest() if self.use_defaults else None

        with self._modified_cmakelists(pruned_dirs, work_dir):
            with self._gitmodules_status():
                # run build_py & manifest.in processing
                super().run()


    def _create_cmake_manifest(self):

        # get dict of cmakelists texts (keyed by their dir names)
        cmakelists = self.distribution.cmakelists

        # add main CMakeLists.txt
        manifest = ["include CMakeLists.txt"]

        # - add all root's subdirs that CMake traverses to
        graft_dirs = []
        for dir in cmakelists.keys():
            # make sure it is the highest dir of the group
            if dir and not next((dir.startswith(d) for d in graft_dirs), False):
                # remove any that are subdir of dir before adding dir
                graft_dirs = [d for d in graft_dirs if not d.startswith(dir)] + [dir]
        manifest += [f"graft {dir}" for dir in graft_dirs]
        manifest += [f"recursive-exclude {dir} __pycache__/*" for dir in graft_dirs]

        # - exclude all dirs in `nondist_dirs`
        pruned_dirs = []
        if self.nondist_dirs:
            pruned_dirs = self.nondist_dirs
            manifest += [f"prune {dir}" for dir in pruned_dirs]

        # - if not `include_gitmodules`, exclude all git submodules
        if gitmodules := gitutil.list_submodules():
            if not self.include_gitmodules:
                # not including any, prune'em all
                manifest += [f"prune {module.path}" for module in gitmodules.keys()]
            elif self.nondist_gitmodules:
                # if there are non-distribution submodules, prune only those
                manifest += [f"prune {dir}" for dir in self.nondist_gitmodules]
                pruned_dirs += self.nondist_gitmodules

        # remove any files CMake previously installed

        # store the manifest
        self.cmake_manifest = manifest

        return pruned_dirs

    def _add_defaults_ext(self):
        """add cmake manifest"""
        for line in self.cmake_manifest:
            self.filelist.process_template_line(line)
    
    @contextlib.contextmanager
    def _modified_cmakelists(self, pruned_dirs, work_dir):
        # CMakeLists.txt who add_subdirectory() one of pruned dirs must be modified
        mod_cmakelists = {}
        for dir in pruned_dirs:
            for pdir, txt in self.cmakelists.items():
                if dir.startswith(pdir):
                    # use modded text instead if exists
                    txt = mod_cmakelists.get(pdir, txt)
                    reldir = dir[len(pdir) + 1 :]
                    found, txt = cmakeutil.subdir_remove(txt, reldir)
                    if not found:
                        raise DistutilsSetupError(
                            f"Could not find `add_subdirectory({reldir})` command in any CMakeLists.txt files"
                        )

                    mod_cmakelists[pdir] = txt

        # backup then modify CMakeLists.txt files
        for dir, txt in mod_cmakelists.items():
            dst = os.path.join(work_dir, dir)
            os.makedirs(dst, exist_ok=True)
            dst = os.path.join(dst, "CMakeLists.txt")
            src = os.path.join(dir, "CMakeLists.txt")
            os.replace(src, dst)
            with open(src, "wt") as f:
                f.write(txt)

        yield

        # restore the backups of modified CMakeLists.txt files
        for dir, txt in mod_cmakelists.items():
            dst = os.path.join(dir, "CMakeLists.txt")
            src = os.path.join(work_dir, dst)
            os.replace(src, dst)

    @contextlib.contextmanager
    def _gitmodules_status(self):
        # create .gitmodules_status file
        saved = not self.include_gitmodules and gitutil.save_gitmodules(
            excludes=self.nondist_gitmodules
        )

        yield

        # remove the .gitmodules_status file
        if saved:
            gitutil.delete_gitmodules()
