"""Provides download_song to download a song from Youtube Music"""
import subprocess
import re

def download_song(query: str) -> str | None | tuple[str, str]:
    """Downloads a song and parses the output to get the track ID.

    Args:
        query (str): The Spotify track ID to download.

    Returns:
        str | None | tuple[str, str]: Spotify track ID or None if no song found.
    """

    download_cmd = [
        "spotdl",
        f"https://open.spotify.com/track/{query}",
        "--respect-skip-file",
        "--create-skip-file",
        "--output",
        "cache/downloads/{track-id}"
    ]

    convert_cmd = [
        "ffmpeg",
        '-i',
        f'cache/downloads/{query}.mp3',
        '-acodec',
        'pcm_u8',
        '-ar',
        '22050',
        f'cache/downloads/{query}.wav'
    ]
    print(f"query: {query}")

    try:
        result = subprocess.run(
            download_cmd,
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout + result.stderr


        convert_result = subprocess.run(convert_cmd, check=False, capture_output=True, text=True)
        print(convert_result.stderr)

        # Try to find "Downloaded" line
        match = re.search(r'Downloaded\s+"(.+?)":', output)

        # Try to find "Skipping" line
        match = re.search(r'Skipping\s+(.+?)\s+\(skip file found\)', output)
        if match:
            return match.group(1)


        return None
    except Exception as e:
        return ("error", str(e))