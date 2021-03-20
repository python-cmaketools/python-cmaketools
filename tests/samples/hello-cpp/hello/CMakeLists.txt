
# src folder name is used as the target name 
Python3_add_library (_hello SHARED "_hello.cxx")
set_target_properties(_hello PROPERTIES SUFFIX ${PYTHON_MODULE_EXTENSION})


install(TARGETS _hello RUNTIME DESTINATION hello COMPONENT EXT)
# install(TARGETS ${TARGET} DESTINATION ${DST_DIR} COMPONENT "EXT")

set(world "${CMAKE_CURRENT_SOURCE_DIR}/world.py")
file(WRITE ${world} "")

install(FILES ${world} DESTINATION hello)
