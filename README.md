# Syscall Extract

A Python tool to extract syscall information from Linux kernel headers using libclang.

## Overview

Syscall Extract parses Linux kernel headers to extract detailed information about system calls, including:

- Syscall numbers
- Function signatures
- Type definitions for arguments and return values

The extracted information can be output in JSON, C header or a human-readable text.

## Requirements

- Python 3.6+
- libclang (with Python bindings)
- GCC

## Installation

1. Install libclang development files:

   ```bash
   # Ubuntu/Debian
   wget https://apt.llvm.org/llvm.sh
   chmod +x llvm.sh
   sudo ./llvm.sh 17  # Replace with desired LLVM version
   sudo apt-get install libclang-17-dev python3-clang-17
   ```

2. Install the package:

   ```bash
   pip install syscall-extract
   ```

   Or install from source:

   ```bash
   git clone https://github.com/mpsm/syscall-extract.git
   cd syscall-extract
   pip install -e .
   ```

## Usage

Basic usage:

```bash
syscall-extract
```

### Command-line Options

- `--log-level {debug,info,warning,error,critical}`: Set logging level (default: info)
- `--gcc PATH`: Path to GCC binary (default: 'gcc')
- `--output FILE, -o FILE`: Output file path (default: 'syscalls.json')
- `--format {json,text,header}`: Output format (default: json)
- `--libclang-path PATH`: Path to libclang.so (optional, will try to find automatically)

### Output Formats

#### JSON

Contains detailed syscall information including:
- Syscall numbers and names
- Function signatures with parameter details
- Type definitions

```bash
syscall-extract --format json --output syscalls.json
```

#### Text

Human-readable ASCII tables with syscall information grouped by header:

```bash
syscall-extract --format text --output syscalls.txt
```

#### C Header

Generates a C header file with syscall number definitions and function prototypes:

```bash
syscall-extract --format header --output syscalls.h
```

## Troubleshooting

### LibClang Issues

  Use the `--libclang-path` option to explicitly specify the path, if you encounter `libclang` version issues:
   ```bash
   syscall-extract --libclang-path /path/to/libclang.so
   ```

### GCC Issues

If you need to use a specific GCC version:

```bash
syscall-extract --gcc /path/to/specific/gcc
```

## License

[MIT License](LICENSE)
