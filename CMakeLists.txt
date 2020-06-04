cmake_minimum_required(VERSION 3.5)
project(mypkg)

# when installing directly in CMake, redirect its intall root to dist dir
if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set (CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/dist/${PROJECT_NAME}" CACHE PATH "default install path" FORCE )
endif()

# configure pybind & catch2
add_subdirectory("lib/pybind11")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/lib/catch2/contrib")

add_subdirectory("src")

# !!!IMPORTANT!!! Conditionally configure native tests
# Must check the tests folder as typically isn't present in sdist 
if (IS_DIRECTORY "${CMAKE_SOURCE_DIR}/tests")
    add_subdirectory("lib/catch2")
    add_subdirectory("tests")
    enable_testing()
endif(IS_DIRECTORY "${CMAKE_SOURCE_DIR}/tests")
