import os
import shutil
from app.content.measurement_sinks.file_measurement_sink import FileMeasurementSink

from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.utils import platform
from kivy.logger import Logger

from app.ui.part_ui import PartUi
from os.path import join



if platform == 'android':
    from androidstorage4kivy import SharedStorage, Chooser, ShareSheet

class FileMeasurementSinkDownloadUI(BoxLayout, PartUi[FileMeasurementSink]):

    name = 'Download flight data'

    current_value: float | None = None

    last_set: float | None

    def __init__(self, part: FileMeasurementSink, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)
        self.part = part

        if platform != 'android':
            self.add_widget(Label(text='Only supported on android, files are amiable through files system on other platforms', color=[1, 0, 0, 1]))
            return

        self.btn = Button(text='Download')
        self.btn.bind(on_press=self.on_download) # type: ignore
        self.add_widget(self.btn)

    def draw(self):

       pass

    def on_download(self,b):
        # ShareSheet()(self.create_test_uri())
        try:
            files = self.prepare_files_for_download()
            ShareSheet().share_file_list(files)
        except Exception as e:
            Logger.error(f'Failed downloading flight data to device: {e}')


    def prepare_files_for_download(self):

        # Select all files up but not including the current one
        current_files = [f'{self.part.flight_data_folder}/{c}.json' for c in range(1, self.part.current_file_count)] 

        Logger.info(f'Downloading following files: {current_files}')

        shared_storage_locations = []

        i = 0
        for f in current_files:
            i += 1
            filename = join(SharedStorage().get_cache_dir(), f'{i}.json')
            shutil.copyfile(f, filename)
            shared_storage_locations.append(SharedStorage().copy_to_shared(filename))

        return shared_storage_locations
