# Tips to compose compatible `CMakeLists.txt` files

## DO NOT use a variable to specify `source_dir` in `add_subdirectory(source_dir ...)`

Auto-configuration mechanisms in `cmaketools` scans `CMakeLists.txt` and traverse the relevant source subdirectories by following the `add_subdirectory` CMake command in `CMakeLists.txt`. This
traversal mechanism, however, does not parse `CMakeLists.txt` to resolve the CMake variables.

## Create a subdirectory with the extension module name and place `CMakeLists.txt` with a hint text to auto-detect it

`ext_module_hint` option relies on this convention. For example, using pybind11, every extension module is built with `pybind11_add_module()` CMake command. To autodetect pybin11 modules, place this command only in `CMakeLists.txt` in each of the module subdirectories and specify `ext_module_hint=pybind11_add_module` in `setup.cfg`.