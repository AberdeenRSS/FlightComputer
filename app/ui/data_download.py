import asyncio
import os
import shutil
from app.content.measurement_sinks.file_measurement_sink import FileMeasurementSink

from app.helper.global_data_dir import get_user_data_dir
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.utils import platform
from kivy.logger import Logger

from app.ui.part_ui import PartUi
from os.path import join



if platform == 'android':
    from androidstorage4kivy import SharedStorage, Chooser, ShareSheet

class DownloadDataUI(BoxLayout):

    name = 'Download flight data'

    current_value: float | None = None

    last_set: float | None

    complete_future: asyncio.Future

    def __init__(self, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.complete_future = asyncio.Future()

        if platform == 'android':
            
            self.btns = []

            avialable_files = self.get_available_data()

            for f in avialable_files:

                btn = Button(text=f'Download {f}')
                btn.bind(on_press=self.make_on_download(f)) # type: ignore
                self.add_widget(btn)
                self.btns.append(btn)

        else:
            self.add_widget(Label(text='Only supported on android, files are available through files system on other platforms', color=[1, 0, 0, 1]))
            
        complete_btn = Button(text=f'Done')
        complete_btn.bind(on_press=self.on_done) # type: ignore
        self.add_widget(complete_btn)

    def on_done(self, arg):
        self.complete_future.set_result(True)

    def draw(self):

       pass

    def get_available_data(self):
        user_data_dir = get_user_data_dir()

        return [p[0] for p in os.walk(user_data_dir) if p[0].startswith('flight_at_')]
    
    def make_on_download(self, folder):
        def f(arg):
            return self.on_download(folder)
        return f

    def on_download(self, folder):
        # ShareSheet()(self.create_test_uri())
        try:
            files = self.prepare_files_for_download(folder)
            ShareSheet().share_file_list(files)
        except Exception as e:
            Logger.error(f'Failed downloading flight data to device: {e}')


    def prepare_files_for_download(self, folder):

        files = [p[0] for p in os.walk(folder)]

        Logger.info(f'Downloading following files: {files}')

        shared_storage_locations = []

        i = 0
        for f in files:
            i += 1
            filename = join(SharedStorage().get_cache_dir(), f'{i}.json')
            shutil.copyfile(f, filename)
            shared_storage_locations.append(SharedStorage().copy_to_shared(filename))

        return shared_storage_locations
