cmake_minimum_required(VERSION 3.12)
project(PerangLidiPhysics LANGUAGES CXX)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Force C++17 standard (required by pybind11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 1. Natively find Python 3 on your system
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# 2. Ask the discovered Python executable where pybind11 lives
execute_process(
    COMMAND "${Python3_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE RAW_PYBIND11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

# 3. Clean up Windows backslashes (\) into CMake forward slashes (/)
file(TO_CMAKE_PATH "${RAW_PYBIND11_DIR}" SAFE_PYBIND11_DIR)

# 4. Load pybind11 using the safe path
set(pybind11_DIR "${SAFE_PYBIND11_DIR}")
find_package(pybind11 CONFIG REQUIRED)

# 5. Define your Python module target
pybind11_add_module(physics_core physics_core.cpp)

# Ensure the compiled module drops right into your root folder next to main.py
set_target_properties(physics_core PROPERTIES 
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}"
)