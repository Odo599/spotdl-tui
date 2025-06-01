import pygame
import threading
import time

class MusicPlayer():
    """This is a MusicPlayer class, which can load and play music files using pygame.mixer.
    """
    def __init__(self, queue: list[str] = [], on_song_end_hook = None):
        """Initialises the MusicPlayer class.

        Args:
            queue (list[str], optional): List of paths to music to add to queue. Defaults to [].
        """
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)

        self.queue = queue

        self._paused = False
        self._watch_song_end_thread = threading.Thread(target=self._watch_song_end)
        self._watch_song_end_started = False
        self.on_song_end_hook = on_song_end_hook
        self._quitting = False

    def _watch_song_end(self):
        was_playing = False
        while not self._quitting:
            is_playing = pygame.mixer.music.get_busy()
            if was_playing and not is_playing and not self._paused:
                self.on_song_finish()
            was_playing = is_playing
            time.sleep(0.5)

    def load_song(self, path: str = ""):
        """Loads a song for pygame, will load 0th song in queue if path not provided.

        Args:
            path (str, optional): The path of the song to play. Defaults to "".
        """
        if not self._watch_song_end_started:
            self._watch_song_end_thread.start()
            self._watch_song_end_started = True
        if len(path) > 0:
            pygame.mixer.music.load(path)
        else:
            pygame.mixer.music.load(self.queue[0])

        pygame.mixer.music.play()

    def play(self):
        pygame.mixer.music.unpause()
        self._paused = False

    def pause(self):
        pygame.mixer.music.pause()
        self._paused = True

    def on_song_finish(self):
        if self.on_song_end_hook is not None:
            self.on_song_end_hook()

    def stop(self):
        pygame.mixer.music.stop()
        self._paused = False

    def quit(self):
        self._quitting = True
        pygame.mixer.quit()

