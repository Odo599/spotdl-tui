from player import MusicPlayer
from download import download_song
import os
import logging
import time
import threading

from collections.abc import Callable


logger = logging.getLogger(__name__)


class MusicManager():
    def __init__(self, queue:list[str]=[]):
        self.paused = True
        self.player = MusicPlayer(on_song_end_hook=self.on_song_end)
        self.queue: list[str] = queue
        self._downloaded_songs: list = self._parse_downloaded_file_index()
        self.currently_playing: str | None = None

        self.on_song_change = None
        self.on_queue_change = None

        self._download_manager_thread = threading.Thread(target=self.download_manager)
        self._download_manager_thread.daemon = True
        self._download_manager_thread.start()

    def set_on_song_change(self, on_song_change: Callable):
        self.on_song_change = on_song_change

    def call_on_song_change(self):
        if self.on_song_change is not None:
            self.on_song_change()

    def set_on_queue_change(self, on_queue_change):
        self.on_queue_change = on_queue_change

    def call_on_queue_change(self):
        if self.on_queue_change is not None:
            self.on_queue_change()

    def _parse_downloaded_file_index(self):
        """Reads cache/downloaded.txt, and returns each line stripped of newline.

        Returns:
            list[str]: List of each line in cache/downloaded.txt
        """
        with open('cache/downloaded.txt') as f:
            lines = f.readlines()
            return [line.rstrip('\n') for line in lines]

    def download_manager(self):
        while True:
            time.sleep(1)
            if len(self.queue) > 0:
                if self.queue[0] not in self._downloaded_songs:
                    logger.info(f"Download Next in Queue: {self.queue[0]}")
                    self.download_song(self.queue[0])

    def pause(self):
        """Attempts to pause currently playing song, and sends notification on error.
        """
        try:
            self.player.pause()
            self.paused = True
        except:
            os.system('notify-send \'Error while pausing\'')

    def unpause(self):
        """Attempts to unpause the currently playing song, and sends notification on error.
        """
        try:
            self.player.play()
            self.paused = False
        except:
            os.system('notify-send \'Error while unpausing\'')

    def force_play_song(self, track_id: str, clear_queue: bool = False):
        """Loads song immediately, but does not play it (call MusicManager.unpause). Will clear the queue if clear_queue is true.

        Args:
            track_id (str): The spotify track id of the song to play.
            clear_queue (bool, optional): Set to true to clear the queue. Defaults to False.
        """
        self.player.stop()
        if track_id not in self._downloaded_songs or not os.path.exists(f'cache/downloads/{track_id}.mp3'):
            self.download_song(track_id)
        self.load_song(track_id)
        self.currently_playing = track_id
        if clear_queue:
            self.reset_queue()

        self.call_on_song_change()

    def reset_queue(self):
        """Sets the queue to an empty list.
        """
        self.queue = []

    def add_song_to_queue(self, track_id: str, call_on_queue_change: bool = True):
        """Adds a track to the queue.

        Args:
            track_id (str): Spotify track ID to add to queue.
        """
        self.queue.append(track_id)
        if call_on_queue_change:
            self.call_on_queue_change()

    def add_songs_to_queue(self, track_ids: list[str]):
        """Adds a list of tracks to the queue.

        Args:
            track_ids (list[str]): List of track ids to add to the queue.
        """
        for track in track_ids:
            self.add_song_to_queue(track, False)

        self.call_on_queue_change()

    def download_song(self, track_id: str, force: bool = False):
        """Calls SpotDL to download a song if not already downloaded

        Args:
            track_id (str): Spotify track ID to download.
            force (bool): Set to true to download even if already downloaded.
        """
        if track_id not in self._downloaded_songs or force:
            logger.info(f"Downloading: {track_id}")
            download_song(f"https://open.spotify.com/track/{track_id}")
            with open('cache/downloaded.txt', "a") as f:
                f.write(f'\n{track_id}')
                self._downloaded_songs.append(track_id)

    def load_song(self, track_id: str):
        """Loads a track in python with full path.

        Args:
            track_id (str): Spotify track ID to load.
        """
        self.player.load_song(f"cache/downloads/{track_id}.mp3")
        self.currently_playing = track_id
        self.paused = True

        self.call_on_song_change()

    def on_song_end(self):
        """Runs when the currently playing song ends (don't call)
        """
        self.currently_playing = None
        self.paused = True
        if len(self.queue) > 0:
            self.currently_playing = self.queue[0]
            self.force_play_song(self.queue[0])
            self.queue.pop(0)

            self.call_on_song_change()

    def play_queue(self):
        """Plays the first song in the queue.
        """
        logger.info(f"Playing {self.queue[0]}")
        self.force_play_song(self.queue[0])
        self.queue.pop(0)

        self.call_on_song_change()
        self.call_on_queue_change()

    def skip_forward(self):
        if len(self.queue) < 1:
            return False
        else:
            logger.info(f"Skipping to {self.queue[0]} from {self.currently_playing}")
            self.pause()
            self.force_play_song(self.queue[0])
            self.queue.pop(0)
            self.call_on_song_change()
            self.call_on_queue_change()

    def quit(self):
        """Stops playback and quits pygame.
        """
        self.paused = True
        self.currently_playing = None
        self.player.stop()
        self.player.quit()