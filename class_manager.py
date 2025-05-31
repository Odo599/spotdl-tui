"""Module providing a class with all classes used in spotdl-tui"""
import logging

from textual.logging import TextualHandler

from music_manager import MusicManager as mm
from player import MusicPlayer as mp
from song_metadata import SongMetadataFile as sm
from spotify import SpotifyClient as sc



class ClassManager():
    """A class to manage all the other classes used in spotdl-tui"""
    def __init__(
        self,
        music_manager = mm(),
        music_player = mp(),
        song_metadata_file = sm(),
        spotify_client = sc(),
        logger: logging.Logger = logging.getLogger()
        ):

        self.music_manager = music_manager
        self.music_player = music_player
        self.song_metadata_file = song_metadata_file
        self.spotify_client = spotify_client
        self.logger = logger

        if self.music_manager is None:
            self.music_manager = mm()

        if self.music_player is None:
            self.music_player = mp()

        if self.song_metadata_file is None:
            self.song_metadata_file = sm()

        if self.spotify_client is None:
            self.spotify_client = sc()
            self.spotify_client.authenticate()

        if logger is None:
            self.logger = logging.getLogger()
            self.logger.setLevel(logging.INFO)

            handler = TextualHandler()
            handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter("%(levelname)s [%(filename)s:%(lineno)d]: %(message)s")
            handler.setFormatter(formatter)

            self.logger.addHandler(handler)

        self.spotify_client.authenticate()
