#!/bin/bash
# compile.sh
# ----------
# Compiles all C++ source files into executables.
# Run this script once before starting the Streamlit app.
#
# Usage: bash cpp/compile.sh

# Create executables directory if it doesn't exist
mkdir -p executables

echo "Compiling bankers.cpp..."
g++ -o executables/bankers cpp/bankers.cpp
if [ $? -eq 0 ]; then
    echo "  ✓ bankers compiled successfully"
else
    echo "  ✗ Failed to compile bankers.cpp"
    exit 1
fi

echo "Compiling deadlock.cpp..."
g++ -o executables/deadlock cpp/deadlock.cpp
if [ $? -eq 0 ]; then
    echo "  ✓ deadlock compiled successfully"
else
    echo "  ✗ Failed to compile deadlock.cpp"
    exit 1
fi

echo "Compiling cycle_detection.cpp..."
g++ -o executables/cycle_detection cpp/cycle_detection.cpp
if [ $? -eq 0 ]; then
    echo "  ✓ cycle_detection compiled successfully"
else
    echo "  ✗ Failed to compile cycle_detection.cpp"
    exit 1
fi

echo ""
echo "All C++ files compiled! Executables are in the 'executables/' folder."
