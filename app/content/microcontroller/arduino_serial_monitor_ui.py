
from typing import Iterable, Sized, Collection, Union
from app.content.microcontroller.arduino_serial import ArduinoOverSerial
from app.content.microcontroller.arduino_serial_common import RssPacket
from app.ui.part_ui import PartUi

from time import time
from datetime import datetime

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button

class ArduinoSerialMonitorUI(BoxLayout, PartUi[ArduinoOverSerial]):

    name = 'Serial Monitor'

    message_labels: list[Label]

    messages: list[RssPacket]


    def __init__(self, part: ArduinoOverSerial, max_messages: int = 10,  **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.message_labels = []
        self.messages = []

        self.max_messages = max_messages

        self.part = part

    def draw(self):

        # Nothing new to draw
        if self.part.last_message is None or (len(self.messages) > 0 and self.part.last_message == self.messages[-1]):
            return
        
        new_label = Label(text= f'{datetime.fromtimestamp(time()).isoformat()}: {self.part.last_message}')
        
        self.messages.append(self.part.last_message)
        self.message_labels.append(new_label)
        
        self.add_widget(new_label)

        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
            self.remove_widget(self.message_labels.pop(0))

        
