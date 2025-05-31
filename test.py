import unittest
from unittest.mock import patch, MagicMock, mock_open
import logging

from music_manager import MusicManager
import download
import player
import spotify
import class_manager

class TestMusicManager(unittest.TestCase):
    @patch('music_manager.MusicPlayer')
    @patch('music_manager.open', new_callable=mock_open, read_data='track1\ntrack2\n')
    def setUp(self, mock_file, mock_player):
        self.mm = MusicManager()

    def tearDown(self):
        # Ensure background threads and player are stopped after each test
        if hasattr(self, 'mm') and self.mm is not None:
            self.mm.quit()

    @patch('music_manager.open', new_callable=mock_open, read_data='track1\ntrack2\n')
    def test_parse_downloaded_file_index(self, mock_file):
        self.assertEqual(self.mm._downloaded_songs, ['track1', 'track2'])

    @patch('music_manager.MusicPlayer')
    def test_pause_and_unpause(self, mock_player):
        self.mm.player = MagicMock()
        self.mm.pause()
        self.mm.player.pause.assert_called_once()
        self.assertTrue(self.mm.paused)
        self.mm.unpause()
        self.mm.player.play.assert_called_once()
        self.assertFalse(self.mm.paused)

    @patch('music_manager.download_song')
    @patch('music_manager.os.path.exists', return_value=True)
    @patch('music_manager.MusicPlayer')
    def test_force_play_song_downloaded(self, mock_player, mock_exists, mock_download):
        self.mm._downloaded_songs = ['track1']
        self.mm.player = MagicMock()
        self.mm.load_song = MagicMock()
        self.mm.force_play_song('track1')
        self.mm.load_song.assert_called_with('track1')
        self.assertEqual(self.mm.currently_playing, 'track1')

    @patch('music_manager.download_song')
    @patch('music_manager.os.path.exists', return_value=False)
    @patch('music_manager.MusicPlayer')
    def test_force_play_song_not_downloaded(self, mock_player, mock_exists, mock_download):
        self.mm._downloaded_songs = []
        self.mm.player = MagicMock()
        self.mm.load_song = MagicMock()
        self.mm.download_song = MagicMock()
        self.mm.force_play_song('track3')
        self.mm.download_song.assert_called_with('track3')
        self.mm.load_song.assert_called_with('track3')

    def test_add_song_to_queue(self):
        self.mm.add_song_to_queue('trackX')
        self.assertIn('trackX', self.mm.queue)

    @patch('music_manager.download_song')
    @patch('music_manager.open', new_callable=mock_open)
    def test_download_song(self, mock_file, mock_download):
        self.mm._downloaded_songs = []
        self.mm.download_song('trackY')
        mock_download.assert_called()
        mock_file().write.assert_called()

    @patch('music_manager.MusicPlayer')
    def test_load_song(self, mock_player):
        self.mm.player = MagicMock()
        self.mm.load_song('trackZ')
        self.mm.player.load_song.assert_called()
        self.assertEqual(self.mm.currently_playing, 'trackZ')
        self.assertTrue(self.mm.paused)

class TestDownload(unittest.TestCase):
    @patch('subprocess.run')
    def test_download_song_success(self, mock_run):
        mock_run.return_value.stdout = 'Downloaded "Song":\n'
        mock_run.return_value.stderr = ''
        result = download.download_song('https://open.spotify.com/track/trackid')
        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_download_song_skip(self, mock_run):
        mock_run.return_value.stdout = ''
        mock_run.return_value.stderr = 'Skipping trackid (skip file found)\n'
        result = download.download_song('https://open.spotify.com/track/trackid')
        self.assertEqual(result, 'trackid')

    @patch('subprocess.run', side_effect=Exception('fail'))
    def test_download_song_error(self, mock_run):
        result = download.download_song('https://open.spotify.com/track/trackid')
        self.assertTrue(result is None or (isinstance(result, tuple) and result[0] == 'error'))

class TestPlayer(unittest.TestCase):
    @patch('player.pygame.mixer')
    def test_load_song(self, mock_mixer):
        p = player.MusicPlayer()
        p.load_song('path/to/song.mp3')
        mock_mixer.music.load.assert_called()
        mock_mixer.music.play.assert_called()

    @patch('player.pygame.mixer')
    def test_play_pause_stop(self, mock_mixer):
        p = player.MusicPlayer()
        p.play()
        mock_mixer.music.unpause.assert_called()
        p.pause()
        mock_mixer.music.pause.assert_called()
        p.stop()
        mock_mixer.music.stop.assert_called()

class TestSpotifyClient(unittest.TestCase):
    @patch('spotify.SpotifyOAuth')
    @patch('spotify.spotipy.Spotify')
    def test_authenticate(self, mock_spotify, mock_oauth):
        client = spotify.SpotifyClient()
        client.authenticate()
        mock_spotify.assert_called()

    @patch('spotify.SpotifyClient.authenticate')
    @patch('spotify.SpotifyClient.get_user_playlists')
    def test_get_user_playlists(self, mock_get, mock_auth):
        mock_get.return_value = [['name', 'id']]
        client = spotify.SpotifyClient()
        client.sp = MagicMock()
        playlists = client.get_user_playlists()
        self.assertIsInstance(playlists, list)

    def test_extract_playlist_id(self):
        client = spotify.SpotifyClient()
        url = 'https://open.spotify.com/playlist/12345abcde'
        self.assertEqual(client._extract_playlist_id(url), '12345abcde')

class TestClassManager(unittest.TestCase):
    def setUp(self):
        # Patch dependencies to avoid real file/network access
        self.patcher_mm = patch('class_manager.mm', autospec=True)
        self.patcher_sm = patch('class_manager.sm', autospec=True)
        self.patcher_sc = patch('class_manager.sc', autospec=True)
        self.mock_mm = self.patcher_mm.start()
        self.mock_sm = self.patcher_sm.start()
        self.mock_sc = self.patcher_sc.start()
        self.addCleanup(self.patcher_mm.stop)
        self.addCleanup(self.patcher_sm.stop)
        self.addCleanup(self.patcher_sc.stop)

    def test_default_initialization(self):
        cm = class_manager.ClassManager()
        self.assertIsNotNone(cm.music_manager)
        self.assertIsNotNone(cm.song_metadata_file)
        self.assertIsNotNone(cm.spotify_client)
        self.assertIsNotNone(cm.logger)

    def test_custom_initialization(self):
        mock_mm_instance = self.mock_mm()
        mock_sm_instance = self.mock_sm()
        mock_sc_instance = self.mock_sc()
        logger = logging.getLogger('test_logger')
        cm = class_manager.ClassManager(
            music_manager=mock_mm_instance,
            song_metadata_file=mock_sm_instance,
            spotify_client=mock_sc_instance,
            logger=logger
        )
        self.assertIs(cm.music_manager, mock_mm_instance)
        self.assertIs(cm.song_metadata_file, mock_sm_instance)
        self.assertIs(cm.spotify_client, mock_sc_instance)
        self.assertIs(cm.logger, logger)

    def test_logger_set_on_music_manager(self):
        mock_mm_instance = self.mock_mm()
        logger = logging.getLogger('test_logger2')
        cm = class_manager.ClassManager(music_manager=mock_mm_instance, logger=logger)
        if hasattr(mock_mm_instance, 'logger'):
            self.assertIs(mock_mm_instance.logger, logger)

    def test_spotify_client_authenticate_called(self):
        mock_sc_instance = self.mock_sc()
        cm = class_manager.ClassManager(spotify_client=mock_sc_instance)
        self.assertTrue(mock_sc_instance.authenticate.called)


if __name__ == '__main__':
    unittest.main()
