from app.content.measurement_sinks.file_measurement_sink import FileMeasurementSink

from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.utils import platform

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
        self.btn.bind(on_press=self.button2_pressed) # type: ignore
        self.add_widget(self.btn)

    def draw(self):

       pass

    def button2_pressed(self,b):
        ShareSheet().share_file(self.create_test_uri())

    def create_test_uri(self):
        # create a file in Private storage
        filename = join(SharedStorage().get_cache_dir(),'test.html')
        with open(filename, "w") as f:
            f.write("<html>\n")
            f.write(" <head>\n")
            f.write(" </head>\n")
            f.write(" <body>\n")
            f.write("  <h1>All we are saying, is<h1>\n")
            f.write("  <h1>give bees a chance<h1>\n")
            f.write(" </body>\n")
            f.write("</html>\n")
        # Insert the test case in this app's Shared Storage so it
        # will have a Uri
        return SharedStorage().copy_to_shared(filename)
