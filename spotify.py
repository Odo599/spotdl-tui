import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import re


class SpotifyClient:
    def __init__(self):
        load_dotenv()
        self.scope = "playlist-read-private playlist-read-collaborative"
        self.redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
        self.client_id = os.getenv("SPOTIPY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        self.sp = None

    def authenticate(self):
        """Authenticate with Spotify and initialize the client."""
        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    def get_user_playlists(self):
        """Returns a list of all the playlist the authenticated user has created.

        Raises:
            Exception: If Spotify client not authenticated.

        Returns:
            list[list[str]]: list of lists of format [name, id]
        """
        if not self.sp:
            raise Exception("Spotify client not authenticated. Call authenticate() first.")

        playlists = []
        results = self.sp.current_user_playlists()
        while results:
            for item in results['items']:
                playlists.append([
                    item['name'],
                    item['id']
                ])
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        return playlists

    def get_playlist_tracks(self, playlist_url):
        """Gets all the tracks of Spotify playlist, with track name, artist name, and id.

        Args:
            playlist_url (_type_): URL of the playlist to get.

        Raises:
            Exception: If Spotify client not authenticated.
            ValueError: If Spotify playlist URL is invalid.

        Returns:
            list[str]: list of [name, artists, id]
        """
        if not self.sp:
            raise Exception("Spotify client not authenticated. Call authenticate() first.")

        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError("Invalid Spotify playlist URL.")

        tracks = []
        results = self.sp.playlist_items(playlist_id)
        while results:
            for item in results['items']:
                track = item['track']
                name = track['name']
                href = track['id']
                artists = ", ".join(artist['name'] for artist in track['artists'])
                tracks.append([name, artists, href])
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        return tracks

    def get_playlist_metadata(self, playlist_url:str):
        """Gets playlist metadata.

        Args:
            playlist_url (str): The URL of the playlist to get.

        Raises:
            Exception: If Spotify client not authenticated.
            ValueError: If Spotify playlist URL is invalid.
            ValueError: Failed to extract metadata.

        Returns:
            _type_: _description_
        """
        if not self.sp:
            raise Exception("Spotify client not authenticated. Call authenticate() first.")

        playlist_id = self._extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError("Invalid Spotify URL.")

        results = self.sp.playlist(playlist_id)

        if type(results) == dict:
            return {'name':results['name']}
        else:
            raise ValueError("Could not get metadata.")

    def download_song_metadata(self, song_id:str) -> dict[str, str] | None:
        if not self.sp:
            raise Exception("Spotify client not authenticated. Call authenticate() first.")

        response = self.sp.track(song_id)
        if response != None:
            to_return = {
                'album-id':     response['album']['id'],
                'album-name':   response['album']['name'],
                'name':         response['name'],
                'artist-id':    response['artists'][0]['id'],
                'artist-name':  response['artists'][0]['name'],
                'id':           response['id']
            }
        else:
            to_return = None

        return to_return

    def _extract_playlist_id(self, url):
        """Extract playlist ID from a full Spotify playlist URL."""
        match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
        return match.group(1) if match else None
