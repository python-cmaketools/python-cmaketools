# variable to hold the path to src folder to compute relative path of its decendents
set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR})

add_subdirectory("example_module")
add_subdirectory("subpackage")
add_subdirectory("assets")

# copy all the py module files to dist folder
file(GLOB PYFILES LIST_DIRECTORIES false RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "*.py")
install(FILES ${PYFILES} DESTINATION "." COMPONENT "PY") # copy all the py-files in the base source dir
