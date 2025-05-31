from textual.app import App, ComposeResult
from textual.widgets import DataTable, Label, Button, Static, Collapsible, ContentSwitcher
from textual.containers import HorizontalGroup, VerticalGroup, Horizontal
from textual import on
from textual.coordinate import Coordinate
from textual.logging import TextualHandler

import threading
import logging
import random

from spotify import SpotifyClient
from music_manager import MusicManager
from song_metadata import SongMetadataFile

class PlaylistView(Static):
    def __init__(self, playlist_id:str|None = None, *args, **kwargs):
        self.playlist_id = playlist_id
        super().__init__(*args, **kwargs)
        
    def compose(self):
        if self.playlist_id is not None:
            # Setup Data
            table = [
                ("x", "Track Name", "Artist", "id"),
            ]
            tracks = spotify.get_playlist_tracks(f'https://open.spotify.com/playlist/{self.playlist_id}')
            self.playlist_tracks = tracks
            tracks = [['▶'] + sublist for sublist in tracks]
            
            name = spotify.get_playlist_metadata(f'https://open.spotify.com/playlist/{self.playlist_id}')['name']
            
            self.playlist_name = name
            
            # Setup Elements
            self.table = DataTable(id='playlist')
            self.title = Label(name, id='playlist-title')
            self.shuffle = Button("Shuffle", id='playlist-shuffle')
            self.play_all = Button("Play", id='playlist-play')
            
            
            self.table.add_columns(*table[0])
            self.table.add_rows(tracks)
            
            play_group = HorizontalGroup(self.shuffle, self.play_all, id='playlist-play-group')
            
            topbar = HorizontalGroup(self.title, play_group, id="playlist-topbar")
            
            v_group = VerticalGroup(topbar, self.table)
            
            yield v_group
        else:
            yield Label("No Playlist")
    
    # Run when playlist selected
    @on(DataTable.CellSelected)
    async def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        if event.control.id == 'playlist':
            row, column = event.coordinate
            if column == 0:            
                def _task():
                    music_manager.force_play_song(self.table.get_cell_at(Coordinate(row, column + 3)), True)
                    
                _task_thread = threading.Thread(target=_task)
                _task_thread.daemon = True
                _task_thread.start()
    
    @on(Button.Pressed)
    def handle_playlist_selected(self, event: Button.Pressed) -> None:
        if event.control.id == 'playlist-play':
            logger.info(f"Play playlist: {self.playlist_id} ({self.playlist_name})")
            track_ids = [track[-1] for track in self.playlist_tracks]
            music_manager.reset_queue()
            music_manager.add_songs_to_queue(track_ids)
            music_manager.play_queue()
        elif event.control.id == 'playlist-shuffle':
            logger.info(f"Shuffle playlist: {self.playlist_id} ({self.playlist_name})")
            track_ids = [track[-1] for track in self.playlist_tracks]
            random.shuffle(track_ids)
            logger.info(track_ids)
            
            music_manager.reset_queue()
            music_manager.add_songs_to_queue(track_ids)
            music_manager.play_queue()
            logger.info(music_manager.queue)
                  
class PlaylistsView(Static):   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.playlist = PlaylistView()

    def compose(self) -> ComposeResult:
        data = spotify.get_user_playlists()
        data = [['x'] + sublist for sublist in data]
        
        self.table = DataTable(id='playlists')
        self.table.add_columns(*("x", "Name", "ID"))
        self.table.add_rows(data)
        
        yield Collapsible(self.table, collapsed=False, title="Playlists")
        yield self.playlist
    
    # Run when a cell is selected
    @on(DataTable.CellSelected)
    def handle_cell_selected(self, event: DataTable.CellSelected) -> None:
        if event.control.id == 'playlists':
            def _task():
                playlist_id = event.control.get_cell_at(Coordinate(event.coordinate[0], 2))
                logger.info(f"Selected: {event.control.get_cell_at(Coordinate(event.coordinate[0],1))} ({event.control.get_cell_at(Coordinate(event.coordinate[0],2))})")
                # UI update in main thread
                def update_ui():
                    self.playlist.remove()
                    self.playlist = PlaylistView(playlist_id)
                    self.mount(self.playlist)
                self.app.call_from_thread(update_ui)
            threading.Thread(target=_task, daemon=True).start()
    
class BottomBar(Static):
    def compose(self) -> ComposeResult:  
        # TODO Currently Playing
        # TODO View song progress
        
        self.current_play_label =  Label("Currently Playing", id='current')
        yield self.current_play_label
        yield HorizontalGroup(
            Button("Play/Pause", id='play'),
            Button("Next Song", id='next')
        )
        
        music_manager.set_on_song_change(self.update_currently_playing)
    
    def update_currently_playing(self):
        if music_manager.currently_playing != None:
            self.current_play_label.update(music_manager.currently_playing)
    
    # Run when button pressed
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == 'play':
            logger.info(f"Currently Playing: {music_manager.currently_playing}")
            if music_manager.currently_playing is not None:
                if music_manager.paused:
                    music_manager.unpause()
                else:
                    music_manager.pause()
                    
                # self.current_play_label.update(music_manager.currently_playing)
                    
        elif event.button.id == 'next':
            music_manager.skip_forward()    
     
class Queue(Static):
    def compose(self) -> ComposeResult:
        yield Label("Queue")
        self.table = DataTable()
        self.table.add_columns(*("Song",))
        yield self.table
        yield Label(f"{music_manager.queue}")
        
        music_manager.set_on_song_change(self.on_queue_change)
        
    def on_queue_change(self):
        logger.info("Queue Changed")
        self.table.clear()
        self.table.add_rows(self.parse_queue(music_manager.queue))
        
        
    def parse_queue(self, queue: list[str]):
        metadata = song_metadata.read()
        for song_id in queue:
            if metadata.get(song_id) == None:
                new_metadata = spotify.download_song_metadata(song_id)
                if new_metadata != None:
                    song_metadata.add_metadata((new_metadata['id'], new_metadata))
                    
        read_again = song_metadata.read()
        new_data = []
        for i in range(len(queue)):
            new_data.append([read_again[queue[i]]['name']])
        
        return new_data
            
class ViewSwitcher(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(id='switcher-buttons'):
            yield Button("Home", id='switcher-home', classes='switcher-button')
            yield Button("Queue", id='switcher-queue', classes='switcher-button')
            
        with ContentSwitcher(initial="switcher-home"):
            yield PlaylistsView(id='switcher-home')
            yield Queue(id='switcher-queue')
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ['switcher-home', 'switcher-queue']:
            self.query_one(ContentSwitcher).current = event.button.id
    
class Main(App):
    CSS_PATH = 'main.tcss'
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # yield PlaylistsView()        yield PlaylistsView()
        yield ViewSwitcher()
        yield BottomBar()
        # TODO Some way to view the queue
        
if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = TextualHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s [%(filename)s:%(lineno)d]: %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    
    music_manager = MusicManager()
    
    song_metadata = SongMetadataFile()

    spotify = SpotifyClient()
    spotify.authenticate()

    
    
    Main().run()
    music_manager.quit()
