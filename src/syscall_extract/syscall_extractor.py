import logging
from typing import Dict

from .header_utils import expand_macros, expand, find_header_files
from .function_extractor import extract_extern_functions
from .model import Syscall, SyscallsContext

# System headers that might contain syscall information
# Complete list of POSIX headers organized by functionality
SYSTEM_HEADERS = [
    # Core syscall headers checked first
    "unistd.h",  # Most POSIX system calls
    # Process and signals
    "signal.h",  # Signals
    "sys/wait.h",  # Process control
    "sys/resource.h",  # Resource operations
    "sys/times.h",  # Process times
    "spawn.h",  # Process spawn
    "pthread.h",  # Threads
    "sched.h",  # Execution scheduling
    # File system and I/O
    "fcntl.h",  # File control options
    "sys/stat.h",  # File status
    "sys/statvfs.h",  # File system information
    "dirent.h",  # Directory entries
    "ftw.h",  # File tree traversal
    "glob.h",  # Pathname pattern matching
    "sys/select.h",  # Select types
    "poll.h",  # Polling and multiplexing
    "aio.h",  # Asynchronous I/O
    "utime.h",  # File access and modification times
    # Memory management
    "sys/mman.h",  # Memory management declarations
    # IPC (Interprocess Communication)
    "sys/ipc.h",  # IPC access structure
    "sys/msg.h",  # Message queues
    "sys/sem.h",  # Semaphore operations
    "sys/shm.h",  # Shared memory objects
    "mqueue.h",  # Message queues
    "semaphore.h",  # Semaphores
    # Networking
    "sys/socket.h",  # Sockets interface
    "netinet/in.h",  # Internet address family
    "netinet/tcp.h",  # TCP protocol
    "arpa/inet.h",  # Internet operations
    "net/if.h",  # Network interface operations
    "netdb.h",  # Network database operations
    "sys/un.h",  # UNIX domain sockets
    # System information
    "sys/utsname.h",  # System name
    "sys/uio.h",  # Vector I/O operations
    # Terminal I/O
    "termios.h",  # Terminal I/O
    # Date and time
    "time.h",  # Time types
    "sys/time.h",  # Time types
    # User and group information
    "pwd.h",  # Password structure
    "grp.h",  # Group database
    "utmpx.h",  # User accounting database
    # Other standard POSIX headers
    "dlfcn.h",  # Dynamic linking
    "fnmatch.h",  # Filename matching
    "regex.h",  # Regular expressions
    "wordexp.h",  # Word expansion
    "langinfo.h",  # Language information constants
    "nl_types.h",  # Message catalogs
    "syslog.h",  # System error logging
]


def extract_syscall_numbers(expanded_content: str) -> Dict[str, int]:
    """Extract syscall numbers from expanded content."""
    logging.debug("Extracting syscall numbers from macro definitions")
    syscall_numbers = {}

    # Look for lines like "#define __NR_read 0"
    lines = expanded_content.splitlines()
    logging.debug(f"Processing {len(lines)} macro definitions")

    nr_count = 0
    NR_PATTERN = "__NR_"

    for line in lines:
        # Skip lines that don't contain __NR_ prefix
        if NR_PATTERN not in line:
            continue

        parts = line.split()
        # Skip malformed define lines
        if len(parts) < 3 or parts[0] != "#define":
            continue

        _, name, number = parts[:3]
        original_name = name

        # Skip non-syscall macros
        if not name.startswith(NR_PATTERN):
            continue

        name = name[len(NR_PATTERN):]
        nr_count += 1

        try:
            syscall_numbers[name] = int(number)
            logging.debug(
                f"Found syscall: {original_name} -> {name} = {number}")
        except ValueError:
            # If it's not a direct number, it might be another macro
            logging.debug(
                f"Skipping non-numeric syscall: {original_name} = {number}")

    logging.debug(f"Found {nr_count} defines")
    logging.debug(f"Extracted {len(syscall_numbers)} unique syscall numbers")

    return syscall_numbers


def extract_syscalls(args) -> SyscallsContext:
    # Step 1: Extract syscall numbers from syscall.h
    syscall_header = "sys/syscall.h"
    logging.info(f"Processing header: {syscall_header}")
    expanded = expand_macros(syscall_header, args.gcc)

    if not expanded:
        logging.error(f"Could not process header: {syscall_header}")
        raise RuntimeError("Failed to extract syscall definitions")

    syscall_numbers = extract_syscall_numbers(expanded)

    # Create initial Syscall objects without function definitions
    syscalls = {}
    for name, number in syscall_numbers.items():
        syscalls[number] = Syscall(
            name=name, number=number, header_name=syscall_header)

    # Step 2: Find header files that might contain function definitions
    found_headers = find_header_files(args.gcc, SYSTEM_HEADERS)
    logging.info(
        f"Found {len(found_headers)} out of {len(SYSTEM_HEADERS)} headers in system paths"
    )

    # Step 3: Extract function definitions from headers and match with syscalls
    syscall_names = set(syscall_numbers.keys())
    functions_by_name = {}
    typedefs_store = {}
    type_store = {}

    for header in found_headers:
        header_content = expand(header, args.gcc)
        if not header_content:
            continue

        # Extract extern functions from each header
        extern_functions, typedefs, types = extract_extern_functions(
            header_content, header
        )

        # Store functions by name for matching with syscalls
        for func in extern_functions:
            if func.name in syscall_names:
                functions_by_name[func.name] = (func, header)

        # Add typedefs to store for later use
        for typedef in typedefs:
            typedefs_store[typedef.name] = typedef

        type_store.update(types)

    # Match functions with syscalls, save required typedefs
    typedefs_needed = set()
    for name, number in syscall_numbers.items():
        if name in functions_by_name:
            func, header = functions_by_name[name]
            syscalls[number].function = func
            syscalls[number].header_name = header
            logging.debug(
                f"Matched syscall {name} with function definition from {header}"
            )

            # Collect typedefs needed for function arguments
            for arg in func.arguments:
                if arg.type in typedefs_store:
                    typedefs_needed.add(typedefs_store[arg.type])

            # Add typedef for return type
            if func.return_type in typedefs_store:
                typedefs_needed.add(typedefs_store[func.return_type])

    logging.debug(
        f"Found {len(syscalls)} syscall definitions, "
        f"{sum(1 for s in syscalls.values() if s.function is not None)} with function definitions"
    )

    logging.debug(
        f"Found {len(typedefs_store)} typedefs in system headers, {len(typedefs_needed)} needed"
    )

    logging.debug(
        f"Found {len(type_store)} unique relevant types in system headers")

    return SyscallsContext(
        syscalls=syscalls, typedefs=list(typedefs_needed), type_store=type_store
    )
