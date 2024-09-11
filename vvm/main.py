import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from packaging.version import Version

from vvm import wrapper
from vvm.exceptions import VyperError
from vvm.install import get_executable


def get_vyper_version() -> Version:
    """
    Get the version of the active `vyper` binary.

    Returns
    -------
    Version
        vyper version
    """
    vyper_binary = get_executable()
    return wrapper._get_vyper_version(vyper_binary)


def compile_source(
    source: str,
    base_path: Union[Path, str] = None,
    evm_version: str = None,
    vyper_binary: Union[str, Path] = None,
    vyper_version: Union[str, Version, None] = None,
) -> Dict:
    """
    Compile a Vyper contract.

    Compilation is handled via the `--combined-json` flag. Depending on the vyper
    version used, some keyword arguments may not be available.

    Arguments
    ---------
    source: str
        Vyper contract to be compiled.
    base_path : Path | str, optional
        Use the given path as the root of the source tree instead of the root
        of the filesystem.
    evm_version: str, optional
        Select the desired EVM version. Valid options depend on the `vyper` version.
    vyper_binary : str | Path, optional
        Path of the `vyper` binary to use. If not given, the currently active
        version is used (as set by `vvm.set_vyper_version`)
    vyper_version: Version, optional
        `vyper` version to use. If not given, the currently active version is used.
        Ignored if `vyper_binary` is also given.

    Returns
    -------
    Dict
        Compiler output. The source file name is given as `<stdin>`.
    """
    compiler_data = json.loads(
        raw_compile_source(
            vyper_binary=vyper_binary,
            vyper_version=vyper_version,
            source=source,
            base_path=base_path,
            evm_version=evm_version,
            output_format="combined_json",
        )
    )

    return {"<stdin>": list(compiler_data.values())[0]}


def compile_files(
    source_files: Union[List, Path, str],
    base_path: Union[Path, str] = None,
    evm_version: str = None,
    vyper_binary: Union[str, Path] = None,
    vyper_version: Union[str, Version, None] = None,
) -> Dict:
    """
    Compile one or more Vyper source files.

    Compilation is handled via the `--combined-json` flag. Depending on the vyper
    version used, some keyword arguments may not be available.

    Arguments
    ---------
    source_files: List
        Path or list of paths of Vyper source files to be compiled.
    base_path : Path | str, optional
        Use the given path as the root of the source tree instead of the root
        of the filesystem.
    evm_version: str, optional
        Select the desired EVM version. Valid options depend on the `vyper` version.
    vyper_binary : str | Path, optional
        Path of the `vyper` binary to use. If not given, the currently active
        version is used (as set by `vvm.set_vyper_version`)
    vyper_version: Version, optional
        `vyper` version to use. If not given, the currently active version is used.
        Ignored if `vyper_binary` is also given.

    Returns
    -------
    Dict
        Compiler output
    """
    return json.loads(
        raw_compile(
            vyper_binary=vyper_binary,
            vyper_version=vyper_version,
            source_files=source_files,
            base_path=base_path,
            evm_version=evm_version,
            output_format="combined_json",
        )
    )


def raw_compile(
    base_path: Union[str, Path, None] = None,
    vyper_binary: Union[str, Path, None] = None,
    vyper_version: Union[str, Version, None] = None,
    output_format: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Compile a Vyper contract with a custom output format.

    Arguments
    ---------
    base_path : Path | str, optional
        Use the given path as the root of the source tree instead of the root
        of the filesystem.
    vyper_binary : str | Path, optional
        Path of the `vyper` binary to use. If not given, the currently active
        version is used (as set by `vvm.set_vyper_version`)
    vyper_version: Version, optional
        `vyper` version to use. If not given, the currently active version is used.
        Ignored if `vyper_binary` is also given.
    output_format: str, optional
        Output format of the compiler. See `vyper --help` for more information.
    **kwargs: Any
        Flags to be passed to Vyper. See vyper_wrapper for more information.

    Returns
    -------
    str
        Process `stdout` output
    """

    if vyper_binary is None:
        vyper_binary = get_executable(vyper_version)

    stdoutdata, stderrdata, command, proc = wrapper.vyper_wrapper(
        vyper_binary=vyper_binary, f=output_format, p=base_path, **kwargs
    )
    return stdoutdata


def raw_compile_source(source: str, *args, **kwargs) -> str:
    """
    Compile a Vyper contract from source code with a custom output format.

    Arguments
    ---------
    source: str
        Vyper contract to be compiled.
    *args: Any
        Arguments to be passed to `raw_compile`
    **kwargs: Any
        Keyword arguments to be passed to `raw_compile`

    Returns
    -------
    str
        Process `stdout` output
    """
    with tempfile.NamedTemporaryFile(suffix=".vy", prefix="vyper-") as source_file:
        source_file.write(source.encode())
        source_file.flush()
        return raw_compile(source_files=[source_file.name], *args, **kwargs)


def compile_standard(
    input_data: Dict,
    base_path: str = None,
    vyper_binary: Union[str, Path] = None,
    vyper_version: Version = None,
) -> Dict:
    """
    Compile Vyper contracts using the JSON-input-output interface.

    See the Vyper documentation for details on the expected JSON input and output formats.

    Arguments
    ---------
    input_data : Dict
        Compiler JSON input.
    base_path : Path | str, optional
        Use the given path as the root of the source tree instead of the root
        of the filesystem.
    vyper_binary : str | Path, optional
        Path of the `vyper` binary to use. If not given, the currently active
        version is used (as set by `vvm.set_vyper_version`)
    vyper_version: Version, optional
        `vyper` version to use. If not given, the currently active version is used.
        Ignored if `vyper_binary` is also given.

    Returns
    -------
    Dict
        Compiler JSON output.
    """

    if vyper_binary is None:
        vyper_binary = get_executable(vyper_version)

    stdoutdata, stderrdata, command, proc = wrapper.vyper_wrapper(
        vyper_binary=vyper_binary, stdin=json.dumps(input_data), standard_json=True, p=base_path
    )

    compiler_output = json.loads(stdoutdata)
    if "errors" in compiler_output:
        has_errors = any(error["severity"] == "error" for error in compiler_output["errors"])
        if has_errors:
            error_message = "\n".join(
                tuple(
                    error.get("formattedMessage") or error["message"]
                    for error in compiler_output["errors"]
                    if error["severity"] == "error"
                )
            )
            raise VyperError(
                error_message,
                command=command,
                return_code=proc.returncode,
                stdin_data=json.dumps(input_data),
                stdout_data=stdoutdata,
                stderr_data=stderrdata,
                error_dict=compiler_output["errors"],
            )
    return compiler_output
