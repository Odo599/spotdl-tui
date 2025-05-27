from textual.app import App, ComposeResult, RenderResult
from textual.widgets import Footer, Header, DataTable, Log, Label, Button, Static, Collapsible
from textual import on
from textual.widget import Widget
from textual.containers import HorizontalGroup
from textual.coordinate import Coordinate
import threading

from spotify import SpotifyClient

from music_manager import MusicManager


music_manager = MusicManager()

spotify = SpotifyClient()
spotify.authenticate()


class PlaylistTable(Static):
    def __init__(self, playlist_id:str|None = None, *args, **kwargs):
        self.playlist_id = playlist_id
        super().__init__(*args, **kwargs)
        
    def compose(self):
        if self.playlist_id is not None:
            table = [
                ("x", "Track Name", "Artist", "id"),
            ]
            tracks = spotify.get_playlist_tracks(f'https://open.spotify.com/playlist/{self.playlist_id}')
            tracks = [['▶'] + sublist for sublist in tracks]
            
            self.table = DataTable()
            
            self.table.add_columns(*table[0])
            self.table.add_rows(tracks)
            yield self.table
        else:
            yield Label("No Playlist")
    
    @on(DataTable.CellSelected)
    async def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        row, column = event.coordinate
        if column == 0:            
            def _task():
                music_manager.force_play_song(self.table.get_cell_at(Coordinate(row, column + 3)), True)
                
            _task_thread = threading.Thread(target=_task)
            _task_thread.start()
            
class PlaylistsView(Static):   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.playlist = PlaylistTable()  # Initialize with no playlist

    def compose(self) -> ComposeResult:
        data = spotify.get_user_playlists()
        data = [['x'] + sublist for sublist in data]
        
        self.table = DataTable()
        self.table.add_columns(*("x", "Name", "ID"))
        self.table.add_rows(data)
        
        yield Collapsible(self.table, collapsed=False, title="Playlists")
        yield self.playlist
    
    @on(DataTable.CellSelected)
    def handle_cell_selected(self, event: DataTable.CellSelected) -> None:
        playlist_id = event.control.get_cell_at(Coordinate(event.coordinate[0], 2))

        # Replace Playlist
        self.playlist.remove()
        self.playlist = PlaylistTable(playlist_id)
        self.mount(self.playlist)
    
class BottomBar(Static):
    def compose(self) -> ComposeResult:  
        yield Label("Currently Playing", id='current')
        yield HorizontalGroup(
            Button("Play/Pause", id='play'),
            Button("Next Song", id='next')
        )
        
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == 'play':
            print(music_manager.currently_playing)
            if music_manager.currently_playing is not None:
                if music_manager.paused:
                    music_manager.unpause()
                else:
                    music_manager.pause()


class Main(App):
    CSS_PATH = 'main.tcss'
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield PlaylistsView()
        yield BottomBar()
        
        # TODO UI

if __name__ == "__main__":
    Main().run()