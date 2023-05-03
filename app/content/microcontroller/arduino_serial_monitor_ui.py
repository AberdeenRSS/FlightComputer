
from typing import Iterable, Sized, Collection, Union
from app.content.microcontroller.arduino_serial import ArduinoSerial
from app.ui.part_ui import PartUi

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button

class ArduinoSerialSelectUI(BoxLayout, PartUi[ArduinoSerial]):

    name = 'Select Serial Device'

    old_device_list: Union[None, Collection[str]] = None

    old_state = ''

    def __init__(self, part: ArduinoSerial,  **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.part = part