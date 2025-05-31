import subprocess
import re
import os

def download_song(query: str) -> str | None | tuple[str, str]:
    """Downloads a song and parses the output to get the track ID.

    Args:
        query (str): The Spotify track ID to download.

    Returns:
        str | None | tuple[str, str]: Spotify track ID or None if no song found.
    """

    cmd = [
        "spotdl",
        query,
        "--respect-skip-file",
        "--create-skip-file",
        "--output",
        "cache/downloads/{track-id}"
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout + result.stderr

        # Try to find "Downloaded" line
        match = re.search(r'Downloaded\s+"(.+?)":', output)

        # Try to find "Skipping" line
        match = re.search(r'Skipping\s+(.+?)\s+\(skip file found\)', output)
        if match:
            return match.group(1)


        return None
    except Exception as e:
        return ("error", str(e))