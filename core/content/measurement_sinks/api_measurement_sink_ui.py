from app.content.measurement_sinks.api_measurement_sink import ApiMeasurementSink
from app.ui.part_ui import PartUi

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class ApiMeasurementSinkUI(BoxLayout, PartUi[ApiMeasurementSink]):

    name = 'API'

    def __init__(self, part: ApiMeasurementSink, **kwargs):
        super().__init__(**kwargs)

        self.part = part

        self.add_widget(Label(text='Measurement Sink widget'))
        self.last_send_duration_label = Label(text='Measurement Sink widget')
        self.add_widget(self.last_send_duration_label)

    def draw(self):
        self.last_send_duration_label.text = f'Last send duration: {self.part.last_send_duration}s'
        