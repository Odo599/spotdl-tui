import unittest
from unittest.mock import patch, MagicMock, mock_open

from music_manager import MusicManager
import download
import player
import spotify

class TestMusicManager(unittest.TestCase):
    @patch('music_manager.MusicPlayer')
    @patch('music_manager.open', new_callable=mock_open, read_data='track1\ntrack2\n')
    def setUp(self, mock_file, mock_player):
        self.mm = MusicManager()

    @patch('music_manager.open', new_callable=mock_open, read_data='track1\ntrack2\n')
    def test_parse_downloaded_file_index(self, mock_file):
        mm = MusicManager()
        self.assertEqual(mm._downloaded_songs, ['track1', 'track2'])

    @patch('music_manager.MusicPlayer')
    def test_pause_and_unpause(self, mock_player):
        mm = MusicManager()
        mm.player = MagicMock()
        mm.pause()
        mm.player.pause.assert_called_once()
        self.assertTrue(mm.paused)
        mm.unpause()
        mm.player.play.assert_called_once()
        self.assertFalse(mm.paused)

    @patch('music_manager.download_song')
    @patch('music_manager.os.path.exists', return_value=True)
    @patch('music_manager.MusicPlayer')
    def test_force_play_song_downloaded(self, mock_player, mock_exists, mock_download):
        mm = MusicManager(['track1'])
        mm._downloaded_songs = ['track1']
        mm.player = MagicMock()
        mm.load_song = MagicMock()
        mm.force_play_song('track1')
        mm.load_song.assert_called_with('track1')
        self.assertEqual(mm.currently_playing, 'track1')

    @patch('music_manager.download_song')
    @patch('music_manager.os.path.exists', return_value=False)
    @patch('music_manager.MusicPlayer')
    def test_force_play_song_not_downloaded(self, mock_player, mock_exists, mock_download):
        mm = MusicManager(['track3'])
        mm._downloaded_songs = []
        mm.player = MagicMock()
        mm.load_song = MagicMock()
        mm.download_song = MagicMock()
        mm.force_play_song('track3')
        mm.download_song.assert_called_with('track3')
        mm.load_song.assert_called_with('track3')

    def test_add_song_to_queue(self):
        mm = MusicManager([])
        mm.add_song_to_queue('trackX')
        self.assertIn('trackX', mm.queue)

    @patch('music_manager.download_song')
    @patch('music_manager.open', new_callable=mock_open)
    def test_download_song(self, mock_file, mock_download):
        mm = MusicManager([])
        mm._downloaded_songs = []
        mm.download_song('trackY')
        mock_download.assert_called()
        mock_file().write.assert_called()

    @patch('music_manager.MusicPlayer')
    def test_load_song(self, mock_player):
        mm = MusicManager([])
        mm.player = MagicMock()
        mm.load_song('trackZ')
        mm.player.load_song.assert_called()
        self.assertEqual(mm.currently_playing, 'trackZ')
        self.assertTrue(mm.paused)

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

if __name__ == '__main__':
    unittest.main()
