
from app.content.sensors.computed.barometric_altitude import BarometricAltitudeSensor
from app.ui.helper.float_input import FloatInput
from app.ui.part_ui import PartUi

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class BarometricAltitudeConfigUI(BoxLayout, PartUi[BarometricAltitudeSensor]):

    name = 'Configure Barometric Altitude'

    current_value: float | None = None

    last_set: float | None

    def __init__(self, part: BarometricAltitudeSensor, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)
        self.part = part

        self.pressure_input = FloatInput(size_hint=(1, 0.2))
        self.pressure_input.bind(text=self.on_text) #type: ignore

        self.status = Label(text='Not a valid number/pressure', size_hint=(1, 0.1), color=[1, 0, 0, 1])

        self.confirm =  Button(text='Set pressure', size_hint=(1, 0.1))
        self.confirm.bind(on_press=self.set_pressure) # type: ignore

        self.redraw()

    def redraw(self):

        self.clear_widgets()
        
        self.add_widget(self.pressure_input)

        if self.current_value is None:
            self.status.text='Not a valid number/pressure'
            self.status.color=[1, 0, 0, 1]
            self.add_widget(self.status)
            return
        
        if self.last_set is not None:
            self.status.text=f'Value set to {self.last_set} hPa'
            self.status.color=[0, 1, 0, 1]
            self.add_widget(self.status)
            return

        self.confirm.text = f'Set sea level pressure to {self.current_value} hPa'
        self.add_widget(self.confirm)

        
    def on_text(self, instance, value: str):

        self.last_set = None

        try:
            num_value = float(value)
            self.current_value = num_value
        except:
            self.current_value = None

        self.redraw()

    def set_pressure(self, v):
        if self.current_value is not None:
            self.last_set = self.current_value
            self.part.pressure_sea_level = self.current_value*100 # Convert to pascal
        
        self.redraw()

    def draw(self):

       pass
