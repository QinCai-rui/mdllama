import asyncio
import os
import sys
from collections.abc import Callable
from functools import wraps
from importlib import metadata
from pathlib import Path

import httpx
from packaging.version import Version, parse

from .types import ParsedResponse


def debounce(wait: float) -> Callable:
    """
    A decorator to debounce a function, ensuring it is called only after a specified delay
    and always executes after the last call.

    Args:
        wait (float): The debounce delay in seconds.

    Returns:
        Callable: The decorated function.
    """

    def decorator(func: Callable) -> Callable:
        last_call = None
        task = None

        @wraps(func)
        async def debounced(*args, **kwargs):
            nonlocal last_call, task
            last_call = asyncio.get_event_loop().time()

            if task:
                task.cancel()

            async def call_func():
                await asyncio.sleep(wait)
                if asyncio.get_event_loop().time() - last_call >= wait:  # type: ignore
                    await func(*args, **kwargs)

            task = asyncio.create_task(call_func())

        return debounced

    return decorator


def throttle(interval: float) -> Callable:
    """
    A decorator to throttle a function, ensuring it is called at most once per interval.
    The first call executes immediately, subsequent calls within the interval are ignored.

    Args:
        interval (float): The throttle interval in seconds.

    Returns:
        Callable: The decorated function.
    """

    def decorator(func: Callable) -> Callable:
        last_called_at = None

        @wraps(func)
        async def throttled(*args, **kwargs):
            nonlocal last_called_at
            now = asyncio.get_event_loop().time()

            if last_called_at is None or now - last_called_at >= interval:
                last_called_at = now
                await func(*args, **kwargs)

        return throttled

    return decorator


def parse_response(input_text: str) -> ParsedResponse:
    """
    Parse a response from the chatbot.
    """

    thought = ""
    response = input_text
    formatted_output = input_text

    # If the response contains a think tag, split the response into the thought process and the actual response
    thought_end = input_text.find("</think>")
    if input_text.startswith("<think>") and thought_end != -1:
        thought = input_text[7:thought_end].lstrip("\n").rstrip("\n").strip()
        response = input_text[thought_end + 8 :].lstrip("\n").rstrip("\n")
        # transform the think tag into a markdown blockquote (for clarity)
        if thought.strip():
            thought = "\n".join([f"> {line}" for line in thought.split("\n")])
            formatted_output = (
                "> ### <thought\\>\n" + thought + "\n> ### </thought\\>\n" + response
            )

    return ParsedResponse(
        thought=thought, response=response, formatted_output=formatted_output
    )


def get_default_data_dir() -> Path:
    """
    Get the user data directory for the current system platform.

    Linux: ~/.local/share/mdllama
    macOS: ~/Library/Application Support/mdllama
    Windows: C:/Users/<USER>/AppData/Roaming/mdllama

    :return: User Data Path
    :rtype: Path
    """
    home = Path.home()

    system_paths = {
        "win32": home / "AppData/Roaming/mdllama",
        "linux": Path(os.getenv("XDG_DATA_HOME") or Path(home / ".local/share"))
        / "mdllama",
        "darwin": Path(
            os.getenv("XDG_DATA_HOME") or Path(home / "Library/Application Support")
        )
        / "mdllama",
    }

    data_path = system_paths[sys.platform]
    return data_path


def semantic_version_to_int(version: str) -> int:
    """
    Convert a semantic version string to an integer.

    :param version: Semantic version string
    :type version: str
    :return: Integer representation of semantic version
    :rtype: int
    """
    try:
        parts = version.split(".")
        if len(parts) == 2:
            # Handle versions like "20250726.4" - treat as major.minor with patch=0
            major, minor, patch = int(parts[0]), int(parts[1]), 0
        elif len(parts) == 3:
            # Handle standard semantic versions like "1.2.3"
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            # Fallback for other formats
            major, minor, patch = 0, 0, 0
            if len(parts) >= 1:
                try:
                    major = int(parts[0])
                except ValueError:
                    major = 0
            if len(parts) >= 2:
                try:
                    minor = int(parts[1])
                except ValueError:
                    minor = 0
            if len(parts) >= 3:
                try:
                    patch = int(parts[2])
                except ValueError:
                    patch = 0
        
        major = major << 16
        minor = minor << 8
        return major + minor + patch
    except (ValueError, IndexError):
        # If all else fails, return 0
        return 0


def int_to_semantic_version(version: int) -> str:
    """
    Convert an integer to a semantic version string.

    :param version: Integer representation of semantic version
    :type version: int
    :return: Semantic version string
    :rtype: str
    """
    major = version >> 16
    minor = (version >> 8) & 255
    patch = version & 255
    return f"{major}.{minor}.{patch}"


async def is_up_to_date() -> tuple[bool, Version, Version]:
    """
    Checks whether mdllama is current.

    :return: A tuple containing a boolean indicating whether mdllama is current, the running version and the latest version
    :rtype: tuple[bool, Version, Version]
    """

    async with httpx.AsyncClient() as client:
        try:
            running_version = parse(metadata.version("mdllama"))
        except metadata.PackageNotFoundError:
            running_version = parse("0.1.0")  # Fallback when not installed as package
        try:
            response = await client.get("https://pypi.org/pypi/mdllama/json")
            data = response.json()
            pypi_version = parse(data["info"]["version"])
        except (httpx.RequestError, KeyError, ValueError):
            # If no network connection, do not raise alarms.
            pypi_version = running_version
    return running_version >= pypi_version, running_version, pypi_version


async def check_ollama() -> bool:
    """
    Check if the Ollama server is up and running
    """
    from .config import envConfig

    up = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(envConfig.OLLAMA_URL)
            up = response.status_code == 200
    except httpx.HTTPError:
        up = False
    finally:
        if not up:
            # Skip notification for now since we don't have reliable app access
            pass

            async def quit_app():
                await asyncio.sleep(10.0)
                try:
                    from .tools.mcp.setup import teardown_mcp_servers

                    await teardown_mcp_servers()
                    exit()

                except ImportError:
                    pass

            asyncio.create_task(quit_app())
    return up
