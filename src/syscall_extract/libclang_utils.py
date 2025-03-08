import os
import sys
import glob
import logging
import subprocess
import pkg_resources
from typing import Optional, Tuple

# Try to import libclang
try:
    from clang import cindex
    from clang.cindex import Config
except ImportError:
    print(
        "ERROR: LibClang Python bindings not available. Install with: pip install clang"
    )
    print("      You also need to install libclang development files.")
    print("      For latest version on Ubuntu, use LLVM's official repository:")
    print("      wget https://apt.llvm.org/llvm.sh")
    print("      chmod +x llvm.sh")
    print("      sudo ./llvm.sh <version> # e.g., sudo ./llvm.sh 17")
    print("      sudo apt-get install libclang-<version>-dev python3-clang-<version>")
    print("      On Fedora/RHEL: sudo dnf install clang-devel")
    sys.exit(1)


def get_python_clang_version() -> Tuple[Optional[str], Optional[int]]:
    """
    Get the version of the installed Python clang module and
    determine the expected libclang version.

    Returns:
        Tuple of (python_clang_version, expected_libclang_version)
        where expected_libclang_version is the major version number
    """
    try:
        python_clang_version = pkg_resources.get_distribution("clang").version

        # Try to extract expected libclang version from module version
        # The version format is typically like "X.Y" where X corresponds to LLVM version
        parts = python_clang_version.split(".")
        if parts and parts[0].isdigit():
            expected_version = int(parts[0])
            return python_clang_version, expected_version

        # If we can't determine from version string, try to check the module itself
        if hasattr(cindex, "__version__"):
            version_str = getattr(cindex, "__version__")
            if version_str and version_str[0].isdigit():
                return python_clang_version, int(version_str[0])

        # If all else fails, return None for expected version
        return python_clang_version, None

    except Exception as e:
        logging.debug(f"Error getting Python clang version: {e}")
        return None, None


def verify_libclang_version(
    libclang_path: str, expected_version: Optional[int]
) -> bool:
    """
    Verify that the found libclang.so file has the expected version
    by checking its SONAME in the dynamic section.

    Returns True if version matches or if verification couldn't be performed.
    """
    if not expected_version:
        logging.warning("No expected libclang version to verify against")
        return True

    try:
        # Run readelf to extract the dynamic section
        cmd = ["readelf", "-d", libclang_path]
        output = subprocess.check_output(cmd, universal_newlines=True)

        # Look for SONAME entry
        import re

        soname_match = re.search(r"SONAME.*\[([^\]]+)\]", output)

        if soname_match:
            soname = soname_match.group(1)
            logging.info(f"Found SONAME: {soname}")

            # Extract version from SONAME (e.g., libclang-18.so.18 -> 18)
            version_match = re.search(r"libclang-(\d+)\.so", soname)

            if version_match:
                actual_version = int(version_match.group(1))
                logging.info(f"Extracted libclang major version: {actual_version}")

                if actual_version == expected_version:
                    logging.info("Libclang version matches expected version")
                    return True
                else:
                    logging.warning(
                        f"Libclang version mismatch: expected {expected_version}, "
                        f"found {actual_version}"
                    )
                    return False

        # If we couldn't find SONAME or extract version, try filename-based approach
        filename = os.path.basename(libclang_path)
        version_match = re.search(r"libclang-(\d+)", filename)

        if version_match:
            actual_version = int(version_match.group(1))
            logging.info(f"Extracted libclang version {actual_version} from filename")
            return actual_version == expected_version

        logging.warning("Could not extract version from SONAME or filename")
        return True  # Continue anyway

    except subprocess.SubprocessError as e:
        logging.warning(f"Error running readelf: {e}")
        return True  # Continue anyway if verification fails
    except Exception as e:
        logging.warning(f"Could not verify libclang version: {e}")
        return True  # Continue anyway if verification fails


def find_libclang() -> str:
    """Try to find libclang.so in common locations. Exit if not found."""
    # First check what version we're expecting
    python_version, expected_version = get_python_clang_version()
    logging.info(
        f"Python clang module version: {python_version}, expected libclang version: {expected_version}"
    )

    if expected_version:
        logging.info(f"Expected libclang major version: {expected_version}")
        # Look for specifically matching versions first
        version_specific_paths = [
            f"/usr/lib/llvm-{expected_version}/lib/libclang.so",
            f"/usr/lib/x86_64-linux-gnu/libclang-{expected_version}*.so",
        ]

        for path in version_specific_paths:
            for found_path in glob.glob(path):
                if os.path.exists(found_path):
                    logging.info(f"Found matching libclang at: {found_path}")
                    return found_path

    # Fall back to general paths if specific version not found
    common_paths = [
        # Ubuntu/Debian paths
        "/usr/lib/llvm-*/lib/libclang.so",
        "/usr/lib/x86_64-linux-gnu/libclang-*.so",
        "/usr/lib/libclang.so",
        # Fedora/RHEL paths
        "/usr/lib64/libclang.so",
    ]

    for path_pattern in common_paths:
        for path in glob.glob(path_pattern):
            if os.path.exists(path):
                logging.info(f"Found libclang at: {path}")
                # Verify the version
                if verify_libclang_version(path, expected_version):
                    return path
                else:
                    logging.warning(
                        f"Version verification failed for {path}, continuing search"
                    )

    # Provide a more helpful error message based on the expected version
    if expected_version:
        raise RuntimeError(
            f"Could not find libclang.so version {expected_version}. "
            f"Please install libclang-{expected_version}-dev package."
        )
    else:
        raise RuntimeError("Could not find libclang.so in common locations")


def check_libclang_path(args):
    if args.libclang_path:
        if os.path.exists(args.libclang_path):
            Config.set_library_file(args.libclang_path)
            logging.info(f"Using user-specified libclang at: {args.libclang_path}")
        else:
            logging.error(f"Specified libclang path not found: {args.libclang_path}")
            sys.exit(1)
    else:
        try:
            libclang_path = find_libclang()
        except RuntimeError as e:
            logging.fatal(f"Failed to find libclang.so: {e}")
            _, expected_version = get_python_clang_version()
            logging.info("You can specify the path manually with --libclang-path")
            logging.info(
                "For latest version on Ubuntu, use LLVM's official repository:"
            )
            logging.info("  wget https://apt.llvm.org/llvm.sh")
            logging.info("  chmod +x llvm.sh")

            if expected_version:
                logging.info(f"  sudo ./llvm.sh {expected_version}")
                logging.info(
                    f"  sudo apt-get install libclang-{expected_version}-dev python3-clang-{expected_version}"
                )
            else:
                logging.info("  sudo ./llvm.sh <version> # e.g., sudo ./llvm.sh 17")
                logging.info(
                    "  sudo apt-get install libclang-<version>-dev python3-clang-<version>"
                )

            sys.exit(1)
        Config.set_library_file(libclang_path)
