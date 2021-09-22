#!/bin/bash
# Test script for continuous integration.

# Stop script early on any error; check variables
set -eu

# Paths to tools installed by ci-install.sh
MAIN_DIR=${PWD}
BUILD_DIR=${PWD}/ci_build
export PATH=${BUILD_DIR}/pru-gcc/bin:${PATH}
PYTHON=${BUILD_DIR}/python-env/bin/python

######################################################################
# Run compile tests for several different MCU types
######################################################################

DICTDIR=${BUILD_DIR}/firmware
mkdir -p ${DICTDIR}

for TARGET in stereotech_config/mcu/*.config ; do
    make clean
    make distclean
    unset CC
    cp ${TARGET} .config
    make olddefconfig
    make V=1
    size out/*.elf
    cp out/klipper.bin ${DICTDIR}/${TARGET}.bin
done


######################################################################
# Verify klippy host software
######################################################################

start_test klippy "Test invoke klippy"
$PYTHON scripts/test_klippy.py -d ${DICTDIR} test/klippy/*.test
finish_test klippy "Test invoke klippy"
