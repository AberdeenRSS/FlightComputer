
from typing import Iterable, Sized, Collection, Union
from app.content.microcontroller.arduino_serial import ArduinoOverSerial
from app.content.microcontroller.arduino_serial_common import ArduinoHwSelectable
from app.ui.part_ui import PartUi

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy import Logger

class ArduinoSerialSelectUI(BoxLayout, PartUi[ArduinoHwSelectable]):

    name = 'Select Serial Device'

    old_device_list: Union[None, Collection[str]] = None

    old_state = ''

    def __init__(self, part: ArduinoHwSelectable, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.part = part

        self.selected_part_label = Label(text='No Part Selected', size_hint=(1, 0.2))
        self.add_widget(self.selected_part_label)

        self.device_options_scroll = ScrollView(do_scroll_x=False, size_hint=(1, 0.6), always_overscroll=True)
        self.device_options_list = BoxLayout(size_hint=(1, 1), orientation='vertical')
        self.device_options_scroll.add_widget(self.device_options_list)
        self.add_widget(self.device_options_scroll)

    def draw(self):

        s_device = self.part.selected_device

        loading = s_device is not None and not s_device.done()

        if loading:
            if self.old_state != 'LOADING':
                self.old_state = 'LOADING'
                self.clear_widgets()
                self.add_widget(Label(text='Trying to connect...'))
            return
        
        self.update_device_list_if_necessary()

        if s_device is not None and not s_device.cancelled():
            exception = s_device.exception()
            if exception is not None:
                if self.old_state != 'ERROR':
                    Logger.error(exception)
                    self.old_state = 'ERROR'
                    self.clear_widgets()
                    self.add_widget(Label(text=f'Error connecting to device {exception.args[0]}', color=[1, 0, 0, 1]))
                    self.add_widget(self.device_options_scroll)
                return
            
        if s_device is not None:

            if self.old_state != 'CONNECTED':
                self.old_state = 'CONNECTED'
                self.clear_widgets()
                self.add_widget(Label(text=f'Connected to {s_device.result()}'))
            return

        if self.old_state == 'DEFAULT':
            return
        
        self.old_state = 'DEFAULT'
        self.selected_part_label.text = 'No Part Selected'

        self.clear_widgets()
        self.add_widget(self.selected_part_label)
        self.add_widget(self.device_options_scroll)

    def update_device_list_if_necessary(self):
        new_device_list = self.part.device_name_list

        if (self.old_device_list is not None and new_device_list is not None) and len(new_device_list) == len(self.old_device_list) and [i for i, j in zip(new_device_list, self.old_device_list) if i == j]:
            return

        self.old_device_list = new_device_list

        self.device_options_list.clear_widgets()

        if new_device_list is None:
            return
        
        for device in new_device_list:
            btn = Button(text=f'Use "{device}"')
            btn.bind(on_press=self.make_on_select_device(device)) # type: ignore
            self.device_options_list.add_widget(btn)

    def make_on_select_device(self, device_name: str):
        def on_select_device(instance):
            self.part.try_connect_device_in_background(device_name)
        return on_select_device