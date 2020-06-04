set(SRC_DIR "${CMAKE_SOURCE_DIR}/src")

set(TEST_BIN "${PROJECT_NAME}_test")
set(SRC_FILES "${SRC_DIR}/example_module/math.cpp"
    "test_main.cpp"
    "test_math.cpp")

# Generate a test executable
add_executable(${TEST_BIN} ${SRC_FILES})
target_include_directories(${TEST_BIN} PUBLIC "${SRC_DIR}/example_module")
target_link_libraries(${TEST_BIN} Catch2::Catch2)

include(CTest)
include(Catch)
catch_discover_tests(${TEST_BIN})

