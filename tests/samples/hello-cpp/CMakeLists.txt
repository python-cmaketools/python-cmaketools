#CMAKE EXAMPLE #1
cmake_minimum_required(VERSION 3.15.0)

project(hello)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# get the suffix for python extension module and store in PYTHON_MODULE_EXTENSION
execute_process (COMMAND "${Python3_EXECUTABLE}" -c "from distutils import sysconfig;print(sysconfig.get_config_var('EXT_SUFFIX'))"
RESULT_VARIABLE _result
OUTPUT_VARIABLE PYTHON_MODULE_EXTENSION
ERROR_QUIET
OUTPUT_STRIP_TRAILING_WHITESPACE)

add_subdirectory(hello) #[[tagged comment test [=[still comment]=] ]]

file(WRITE "${CMAKE_BINARY_DIR}/helloModule.py" "# helloModule.py")
install(FILES "${CMAKE_BINARY_DIR}/helloModule.py" DESTINATION ".")
