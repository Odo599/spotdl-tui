"""Main entry point for spotdl-tui"""

import threading
import random

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Label, Button, Static, Collapsible, ContentSwitcher
from textual.containers import HorizontalGroup, VerticalGroup, Horizontal
from textual import on
from textual.coordinate import Coordinate

from rich.text import Text

from class_manager import ClassManager

class PlaylistView(Static):
    """A Static that takes a playlist_id and displays a DataTable with a few buttons"""

    def __init__(self, classman: ClassManager, playlist_id: str | None = None, *args, **kwargs):
        self.classman = classman
        self.playlist_id = playlist_id

        self.playlist_tracks = []
        self.playlist_name = ""

        self.table = DataTable()
        self.title = Label()
        self.shuffle = Button()
        self.play_all = Button()

        super().__init__()

    def compose(self):
        if self.playlist_id is not None:
            # Setup Data
            table = [
                ("x", "Track Name", "Artist", "id"),
            ]
            tracks = self.classman.spotify_client.get_playlist_tracks(f'https://open.spotify.com/playlist/{self.playlist_id}')
            self.playlist_tracks = tracks
            tracks = [['▶'] + sublist for sublist in tracks]

            name = self.classman.spotify_client.get_playlist_metadata(f'https://open.spotify.com/playlist/{self.playlist_id}')['name']

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
        """Runs when a square in the playlist's DataTable is selected."""
        if event.control.id == 'playlist':
            row, column = event.coordinate
            if column == 0:
                def _task():
                    self.classman.music_manager.force_play_song(self.table.get_cell_at(Coordinate(row, column + 3)), True)

                _task_thread = threading.Thread(target=_task)
                _task_thread.daemon = True
                _task_thread.start()

    @on(Button.Pressed)
    def handle_button_selected(self, event: Button.Pressed) -> None:
        """Runs when the play or shuffle button is pressed"""
        if event.control.id == 'playlist-play':
            track_ids = [track[-1] for track in self.playlist_tracks]
            self.classman.music_manager.reset_queue()
            self.classman.music_manager.add_songs_to_queue(track_ids)
            self.classman.music_manager.play_queue()
        elif event.control.id == 'playlist-shuffle':
            track_ids = [track[-1] for track in self.playlist_tracks]
            random.shuffle(track_ids)
            self.classman.music_manager.reset_queue()
            self.classman.music_manager.add_songs_to_queue(track_ids)
            self.classman.music_manager.play_queue()

class PlaylistsView(Static):
    """Shows all of the users playlist's in a DataTable,
    on selection opens PlaylistView for the selected Playlist"""
    def __init__(self, classman: ClassManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classman = classman
        self.playlist = PlaylistView(classman)
        self.table = DataTable()

    def compose(self) -> ComposeResult:
        data = self.classman.spotify_client.get_user_playlists()
        data = [['x'] + sublist for sublist in data]
        self.table = DataTable(id='playlists')
        self.table.add_columns(*("x", "Name", "ID"))
        self.table.add_rows(data)
        yield Collapsible(self.table, collapsed=False, title="Playlists")
        yield self.playlist

    # Run when a cell is selected
    @on(DataTable.CellSelected)
    def handle_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Run when a playlist is selected.
        Opens the playlist in PlaylistView"""
        if event.control.id == 'playlists':
            def _task():
                playlist_id = event.control.get_cell_at(Coordinate(event.coordinate[0], 2))
                def update_ui():
                    self.playlist.remove()
                    self.playlist = PlaylistView(self.classman, playlist_id)
                    self.mount(self.playlist)
                self.app.call_from_thread(update_ui)
            threading.Thread(target=_task, daemon=True).start()

class BottomBar(Static):
    """Bar at the bottom of the screen that displays currently playing song."""
    def __init__(self, classman: ClassManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classman = classman

        self.current_play_label = Label()

    def compose(self) -> ComposeResult:
        self.current_play_label =  Label("Currently Playing", id='current')
        yield self.current_play_label
        yield HorizontalGroup(
            Button("Play/Pause", id='play'),
            Button("Next Song", id='next')
        )

        self.classman.music_manager.set_on_song_change(self.update_currently_playing)

    def update_currently_playing(self):
        print('DEBUG type(song_metadata_file):', type(self.classman.song_metadata_file))
        if self.classman.music_manager.currently_playing is not None:
            metadata = self.classman.song_metadata_file.get_metadata(self.classman.music_manager.currently_playing)
            if metadata is not None:
                label_text = Text()
                label_text.append(f"{metadata['name']} - ")
                label_text.append(metadata['artist-name'], 'gray0')
                self.current_play_label.update(label_text)

    def on_button_pressed(self, event: Button.Pressed):
        """Run when play or next is clicked."""
        if event.button.id == 'play':
            if self.classman.music_manager.currently_playing is not None:
                if self.classman.music_manager.paused:
                    self.classman.music_manager.unpause()
                else:
                    self.classman.music_manager.pause()

        elif event.button.id == 'next':
            self.classman.music_manager.skip_forward()

class Queue(Static):
    """View to show the current queue."""
    def __init__(self, classman: ClassManager, **kwargs):
        super().__init__(**kwargs)
        self.classman = classman
        self.table = DataTable()

    def compose(self) -> ComposeResult:
        yield Label("Queue")
        self.table = DataTable()
        self.table.add_columns(*("Song",))
        yield self.table
        yield Label(f"{self.classman.music_manager.queue}")

        self.classman.music_manager.set_on_queue_change(self.on_queue_change)

    def on_queue_change(self):
        """To be run when the queue needs to be updated."""
        self.table.clear()
        self.table.add_rows(self.parse_queue(self.classman.music_manager.queue))


    def parse_queue(self, queue: list[str]) -> list[str]:
        print('DEBUG type(song_metadata_file):', type(self.classman.song_metadata_file))
        metadata = self.classman.song_metadata_file.read()
        for song_id in queue:
            if metadata.get(song_id) is None:
                new_metadata = self.classman.spotify_client.download_song_metadata(song_id)
                if new_metadata is not None:
                    self.classman.song_metadata_file.add_metadata((new_metadata['id'], new_metadata))
        read_again = self.classman.song_metadata_file.read()
        new_data = []
        for song_id in queue:
            new_data.append([read_again[song_id]['name']])
        return new_data

class ViewSwitcher(Static):
    """A Static that uses ViewSwitcher and Button to switch views between PlaylistsView and Queue."""
    def __init__(self, classman: ClassManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classman = classman

    def compose(self) -> ComposeResult:
        with Horizontal(id='switcher-buttons'):
            yield Button("Home", id='switcher-home', classes='switcher-button')
            yield Button("Queue", id='switcher-queue', classes='switcher-button')

        with ContentSwitcher(initial="switcher-home"):
            yield PlaylistsView(self.classman, id='switcher-home')
            yield Queue(self.classman, id='switcher-queue')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Run when switcher button pressed, and change view."""
        if event.button.id in ['switcher-home', 'switcher-queue']:
            self.query_one(ContentSwitcher).current = event.button.id

class Main(App):
    """Main class for spotdl-tui."""
    CSS_PATH = 'main.tcss'
    def __init__(self, classman: ClassManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classman = classman

    def compose(self) -> ComposeResult:
        yield ViewSwitcher(self.classman)
        yield BottomBar(classman=self.classman)

if __name__ == "__main__":
    class_manager = ClassManager()

    main = Main(classman=class_manager)

    Main(classman=class_manager).run()
    class_manager.music_manager.quit()
