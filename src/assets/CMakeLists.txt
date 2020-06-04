# copy all files to dist folder
file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
file(GLOB TXTFILES LIST_DIRECTORIES false RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "*.txt")
list(REMOVE_ITEM TXTFILES "CMakeLists.txt")
install(FILES ${TXTFILES} DESTINATION ${DST_DIR} COMPONENT "PY") # copy all the asset .txt files as package_data
