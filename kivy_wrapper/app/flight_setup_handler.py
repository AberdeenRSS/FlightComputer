import asyncio
from logging import getLogger
from typing import Iterable

from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

from asyncio import Future

from core.api_client import RealtimeApiClient
from core.flight_executer import FlightExecuter

from core.logic import to_vessel_and_flight
from kivy_wrapper.app.flight_config import FlightConfig
from kivy_wrapper.app.ui.part_ui import PartUi

from core.api_client import ApiClient

class FlightExecuterUI(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_widget(Label(text='Initializing Flight'))

class ServerHandshakeDeciderWidget(BoxLayout):

    def __init__(self, exception, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.decision_future = Future()

        self.add_widget(TextInput(text=f'Server Handshake failed: {exception}'))

        def on_retry(instance):
            self.decision_future.set_result('RETRY')

        def on_cancel(instance):
            self.decision_future.set_result('CANCEL')

        def on_run_without(instance):
            self.decision_future.set_result('WITHOUT')

        retry_button = Button(text='Retry')
        retry_button.bind(on_press = on_retry) # type: ignore
        self.add_widget(retry_button)

        without_button = Button(text='Run without Server')
        without_button.bind(on_press = on_run_without) # type: ignore
        self.add_widget(without_button)

        cancel_button = Button(text='Cancel')
        cancel_button.bind(on_press = on_cancel) # type: ignore
        self.add_widget(cancel_button)
        
class PartListWidget(BoxLayout):

    cur_selected_part = None

    def __init__(self, part_uis: Iterable[PartUi], **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.part_uis = part_uis
        self.draw_overview()

    def draw_overview(self):

        self.cur_selected_part = None

        self.clear_widgets()

        self.add_widget(Label(text='parts', size_hint=(1, 0.3)))

        for ui in self.part_uis:

            btn = Button(text = ui.name)
            btn.bind(on_press=self.make_on_draw_part(ui)) # type: ignore
            self.add_widget(btn)

    def make_on_draw_part(self, part_ui):
        def on_press(instance):
            self.draw_part(part_ui)
        return on_press

    def draw_part(self, part_ref: PartUi):

        self.cur_selected_part = part_ref

        self.clear_widgets()

        self.add_widget(Label(text=part_ref.name, size_hint=(1, 0.1)))

        self.add_widget(part_ref)

        def on_back(instance):
            self.draw_overview()

        back_btn = Button(text='Back', size_hint=(1, 0.1))
        back_btn.bind(on_press=on_back) # type: ignore
        self.add_widget(back_btn)

    def update_cur_part(self):
        if self.cur_selected_part is None:
            return
        self.cur_selected_part.draw()


class FlightSetupHandler():


    def __init__(self, config: FlightConfig):

        self.logger = getLogger('Flight Setup')

        self.flight_config = config
        self.rocket = config.rocket
        self.api_client = ApiClient(config.auth_code)

        self.ui = FlightExecuterUI()


        self.init_flight_task = asyncio.get_event_loop().create_task(self.init_flight())
        self.control_loop_task = asyncio.get_event_loop().create_task(self.start_exeution_loop())


    async def init_flight(self):
        
        while(True):
            try:

                self.logger.info(f'Starting server setup handshake')

                self.flight = await self.api_client.run_full_setup_handshake(self.rocket, self.flight_config.name)

                self.logger.info(f'Successfully registered with server. Setting up realtime API')

                self.executor = FlightExecuter(self.flight_config.rocket, self.flight, self.api_client)

                self.realtime_client = RealtimeApiClient(self.api_client, self.flight)
                await self.realtime_client.connect(self.executor.make_on_new_command())

                self.logger.info(f'Realtime communication established')

                break
            except Exception as e:

                self.logger.exception(f'Failed connecting to server: {e} {e.args}')

                self.ui.clear_widgets()
                user_decision_widget = ServerHandshakeDeciderWidget(e)
                self.ui.add_widget(user_decision_widget)

                self.logger.info(f'awaiting user decision on how to proceed')

                user_decision = await user_decision_widget.decision_future

                self.logger.info(f'User decided: {user_decision}')

                self.ui.clear_widgets()

                if user_decision == 'CANCEL':
                    return True
                if user_decision == 'RETRY':
                    self.ui.add_widget(Label(text='Retrying to initialize flight'))
                    continue
                
                _, self.flight = to_vessel_and_flight(self.rocket)
                self.realtime_client = None
                break


        self.ui.clear_widgets()

        return False
    
    def make_ui_hook(self):

        def ui_hook():
            self.part_list_widget.update_cur_part()

        return ui_hook


    async def start_exeution_loop(self):
        
        # Before starting the control loop wait for the flight to init
        canceled = await self.init_flight_task

        # Add the part list to the ui
        self.part_list_widget = PartListWidget(self.flight_config.part_uis)
        self.ui.add_widget(self.part_list_widget)

        if canceled:
            self.logger.warning(f'Flight execution loop canceled, aborting')
            return

        await self.executor.run_control_loop(self.make_ui_hook())
        

        
