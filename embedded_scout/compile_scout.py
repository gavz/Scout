#!/usr/bin/python
import os
import sys
import time
import struct
from elementals import Prompter

# Assuming the script is executed from its directory
sys.path.append("../utils")

from scout_compiler  import *
from context_creator import *

##############################
##  Dynamic Configurations  ##
##############################

SCOUT_DIR           = '../scout'

SCOUT_LOADER_ELF    = 'scout_loader.elf'
SCOUT_LOADER_BIN    = 'scout_loader.bin'

EMBEDDED_SCOUT_ELF  = 'embedded_scout.elf'
EMBEDDED_SCOUT_BIN  = 'embedded_scout.bin'

TARGET_ARCH         = ARC_INTEL
TARGET_ENDIANNESS   = True if TARGET_ARCH == ARC_INTEL else False
TARGET_BITNESS      = False # is 32 bits ?

# Scout Functions (in same order as the c code)
symbol_memcpy  		= 0x400a50
symbol_memset  		= 0x400a00
symbol_malloc  		= 0x400a60
symbol_free    		= 0x400990
symbol_socket  		= 0x400b00
symbol_bind    		= 0x400aa0
symbol_listen  		= 0x400a80
symbol_accept  		= 0x400ad0
symbol_connect 		= 0x400af0
symbol_recv    		= 0x4009a0
symbol_send    		= 0x4009e0
symbol_close   		= 0x400a20
# Project Functions (none for now)
project_got         = []

# project files list
project_pic_files   = ['project_plt.c', 'project_globals.c']
project_files       = ['arm_scout.c', 'project_instructions.c'] + project_pic_files

##
# Sets the bsaic architecture flags for our target
##
def setTargetFlags(logger) :
    # 1. Set the architecture
    setScoutArc(TARGET_ARCH, is_32_bits = TARGET_BITNESS, is_little_endian = TARGET_ENDIANNESS, logger = logger)

    # 2. Set the environment
    setScoutEnv(is_pc = False)

    # 3. Set the permission mode
    setScoutMode(is_user = False)

##
# Compiles the scout loader (TCP Server loader)
##
def compileScoutLoader(logger) :
    # 1. Set the target flags
    setTargetFlags(logger)

    # 2. Additional flags: thumb mode (if in ARM)
    setScoutFlags([flag_arc_thumb] if TARGET_ARCH == ARC_ARM else [])

    # 3. Define the working directories
    setWorkingDirs(project_dir = '.', scout_dir = SCOUT_DIR)

    # 4. Generate the used compilation flags (we will rely on the defaults)
    compile_flags, link_flags = generateCompilationFlags(compile_flags = [], link_flags = [], logger = logger)

    # 5. Generate the list of compiled files
    compilation_files = map(lambda f : os.path.join(SCOUT_DIR, f), scout_loader_deps + [scout_server_loader]) + project_pic_files

    # 6. Compile an embedded scout
    logger.info("Starting to compile the scout loader")
    compileEmbeddedScout(compilation_files, compile_flags, link_flags, SCOUT_LOADER_ELF, SCOUT_LOADER_BIN, logger)

    # 7. Place the PIC context in the resulting binary file
    generateGOT(symbol_memcpy, symbol_memset, symbol_malloc, symbol_free, symbol_socket, symbol_bind,
                symbol_listen, symbol_accept, symbol_connect, symbol_recv, symbol_send, symbol_close, project_got, is_thumb = TARGET_ARCH == ARC_ARM)

    # 8. Setup the sizes for the global variables (No variables used at all)
    generateGlobals(scout_vars_size = 0, project_vars_size = 0)

    # 9. Generate the PIC context, and place it in the binary blob
    placeContext(SCOUT_LOADER_BIN, SCOUT_LOADER_BIN, TARGET_ENDIANNESS, TARGET_BITNESS, logger)

    # 10. Finished :)
    return

##
# Compiles the scout project
##
def compileScout(logger) :
    # 1. Set the target flags
    setTargetFlags(logger)

    # 2. Add additional flags:
    #  a) Will use the TCP server for instructions
    #  b) Will use dynamic buffers (malloc) for the received instructions
    setScoutFlags([flag_instructions, flag_dynamic_buffers])

    # 3. Define the working directories
    setWorkingDirs(project_dir = '.', scout_dir = SCOUT_DIR)

    # 4. Generate the used compilation flags (we will rely on the defaults)
    compile_flags, link_flags = generateCompilationFlags(compile_flags = [], link_flags = [], logger = logger)

    # 5. Generate the list of compiled files
    compilation_files = map(lambda f : os.path.join(SCOUT_DIR, f), scout_all_files) + project_files

    # 6. Compile an embedded scout
    logger.info("Starting to compile the embedded scout")
    compileEmbeddedScout(compilation_files, compile_flags, link_flags, EMBEDDED_SCOUT_ELF, EMBEDDED_SCOUT_BIN, logger)

    # 7. Place the PIC context in the resulting binary file
    generateGOT(symbol_memcpy, symbol_memset, symbol_malloc, symbol_free, symbol_socket, symbol_bind,
                symbol_listen, symbol_accept, symbol_connect, symbol_recv, symbol_send, symbol_close, project_got)

    # 8. Setup the sizes for the global variables
    generateGlobals(scout_vars_size = scout_globals_32_size if TARGET_BITNESS else scout_globals_64_size, project_vars_size = 0)

    # 9. Generate the PIC context, and place it in the binary blob
    placeContext(EMBEDDED_SCOUT_BIN, EMBEDDED_SCOUT_BIN, TARGET_ENDIANNESS, TARGET_BITNESS, logger)

    # 10. Finished :)
    return

##
# Prints the usage instructions
##
def printUsage(args) :
    print 'Usage: %s' % (Args[0].split(os.path.sep)[0])
    print 'Exitting'
    exit(1)

##
# Main function
##
def main(args) :
    # Check the arguments (None for now)
    if len(args) != 1 + 0 :
        print 'Wrong amount of arguments, got %d, expected %d' % (len(args) - 1, 0)
        printUsage(args)

    # Create the logger
    prompter = Prompter()

    # Compile the scout's loader (TCP server)
    compileScoutLoader(prompter)
    # Compile the full scout
    compileScout(prompter)

    prompter.info("Finished Successfully")

if __name__ == "__main__" :
    main(sys.argv)
