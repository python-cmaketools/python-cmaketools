import pytest
import cmakeutils

def test_hello():
    hello.say_hello()

# findexe(cmd)
# run(*args, path=findexe("cmake"), **runargs)
# validate(cmakePath=findexe("cmake"))
# configured(buildDir)
# clear(buildDir)
# configure(
#     root_dir,
#     build_dir,
#     *args,
#     build_type="Release",
#     cmakePath=findexe("cmake"),
#     need_msvc=False,
#     **kwargs,
# )
# build(
#     build_dir,
#     *args,
#     build_type=None,
#     parallel=None,
#     cmakePath=findexe("cmake"),
#     **kwargs,
# ):
# install(
#     build_dir,
#     install_dir,
#     *args,
#     build_type=None,
#     cmakePath=findexe("cmake"),
#     **kwargs,
# ):
# ctest(build_dir, ctestPath=findexe("ctest"), **kwargs):
# read_cache(build_dir, vars=None):
# delete_cache(build_dir):
# get_generators(cmakePath=findexe("cmake"), as_list=False):
# get_generator_names(cmakePath=findexe("cmake")):
# generator_changed(generator, build_dir="build", cmakePath=findexe("cmake")):
