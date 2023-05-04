import time
from app.content.measurement_sinks.api_measurement_sink import ApiMeasurementSink
from app.logic.rocket_definition import Part
from app.ui.part_ui import PartUi

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class DefaultPartUI(BoxLayout, PartUi[Part]):

    name = ''

    labels = dict[str, Label]()

    def __init__(self, part: Part, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.part = part
        self.name = f'{part.name} Measurements'

        self.add_labels_for_measurements()


    def add_labels_for_measurements(self):
        for name, type in self.part.get_measurement_shape():
            self.labels[name] = Label(text=name)
            self.add_widget(self.labels[name])

    def update_text(self):

        measurement = self.part.collect_measurements(time.time())

        i = 0
        for name, type in self.part.get_measurement_shape():
            self.labels[name].text = f'{name}: {measurement[-1][i]}'
            i += 1

    def draw(self):
        self.update_text()