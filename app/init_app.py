
import asyncio
from datetime import datetime, timedelta
from app.ui.data_download import DownloadDataUI
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from app.flight_executer import FlightExecuter
from app.rockets.make_spatula import make_spatula
from datetime import datetime
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

from app.helper.vessel_store import get_vessel_auth_code, set_vessel_auth_code

class FlightCreator(BoxLayout):

    def __init__(self, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.creation_complete_future = asyncio.Future()

        old_auth_code = get_vessel_auth_code()

        self.vessel_auth_code_input = TextInput(text=old_auth_code or 'Auth Code')
        self.add_widget(self.vessel_auth_code_input)

        self.flight_name_input = TextInput(text=f'Flight {datetime.now().isoformat()}')
        self.add_widget(self.flight_name_input)

        self.create_btn = Button(text='Create Flight')
        self.create_btn.bind(on_press = self.make_create_flight_callback()) # type: ignore
        self.add_widget(self.create_btn)

    def make_create_flight_callback(self):
        def create_flight(instance):
            without_line_breaks = self.vessel_auth_code_input.text.replace('\n', '').replace('\r', '').replace(' ', '')
            set_vessel_auth_code(without_line_breaks)
            self.creation_complete_future.set_result({'name': self.flight_name_input.text})
        return create_flight

class MainMenu(BoxLayout):
    def __init__(self, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.complete_future = asyncio.Future()

        start_flight_btn = Button(text='Start Flight')
        start_flight_btn.bind(on_press = self.start_flight)
        self.add_widget(start_flight_btn)

        download_data_btn = Button(text='Downlaod Data')
        download_data_btn.bind(on_press = self.download_data)
        self.add_widget(download_data_btn)

    def start_flight(self, arg):
        self.complete_future.set_result('start_flight')

    def download_data(self, arg):
        self.complete_future.set_result('download_data')

class RSSFlightComputer(App):

    label = None

    def build(self):

        # request_permissions([Permission.HIGH_SAMPLING_RATE_SENSORS])

        self.root_layout = BoxLayout(orientation='vertical')

        return self.root_layout

app = RSSFlightComputer()

def init_app():
    return app, run_loop

async def run_loop():

    while(True):

        app.root_layout.clear_widgets()

        main_menu = MainMenu()
        app.root_layout.add_widget(main_menu)

        selected_ui = await main_menu.complete_future

        app.root_layout.clear_widgets()

        if selected_ui == 'download_data':

            download_ui = DownloadDataUI()
            app.root_layout.add_widget(download_ui)
            
            await download_ui.complete_future
        else:
            break


    while(True):

        app.root_layout.clear_widgets()


        flight_creator = FlightCreator()
        app.root_layout.add_widget(flight_creator)

        create_result = await flight_creator.creation_complete_future

        app.root_layout.clear_widgets()

        flight_config = make_spatula()
        flight_config.auth_code = str(get_vessel_auth_code())

        flight_config.name = create_result['name']

        if flight_config.should_add_default_uis:
            flight_config.add_default_uis()

        flight_executor = FlightExecuter(flight_config)
        app.root_layout.add_widget(flight_executor.ui)

        # Wait for the flight to finish or crash
        await flight_executor.control_loop_task

        app.root_layout.remove_widget(flight_executor.ui)


