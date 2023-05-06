import asyncio
import time
from typing import Iterable, cast
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from app.api_client import ApiClient, RealtimeApiClient
from app.flight_config import FlightConfig
from app.logic.commands.command import Command
from app.logic.to_vessel_and_flight import to_vessel_and_flight
from app.models.command import Command as CommandModel
from app.logic.execution import topological_sort
from app.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase, MeasurementsByPart
from app.logic.rocket_definition import Part, Rocket
from app.ui.part_ui import PartUi

class FlightExecuterUI(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_widget(Label(text='Initializing Flight'))

class ServerHandshakeDeciderWidget(BoxLayout):

    def __init__(self, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.decision_future = asyncio.Future()

        self.add_widget(Label(text='Server Handshake failed', size_hint=(1, 0.25)))

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

        self.add_widget(Label(text='Parts', size_hint=(1, 0.3)))

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

        self.add_widget(Label(text=part_ref.name))

        self.add_widget(part_ref)

        def on_back(instance):
            self.draw_overview()

        back_btn = Button(text='Back')
        back_btn.bind(on_press=on_back) # type: ignore
        self.add_widget(back_btn)

    def update_cur_part(self):
        if self.cur_selected_part is None:
            return
        self.cur_selected_part.draw()


class FlightExecuter:

    def __init__(self, flight_config: FlightConfig, max_frame_time: float = 0.001) -> None:
    
        self.flight_config = flight_config
        self.rocket = flight_config.rocket
        self.max_frame_time = max_frame_time
        self.api_client = ApiClient()

        self.ui = FlightExecuterUI()

        self.init_flight_task = asyncio.get_event_loop().create_task(self.init_flight())
        self.control_loop_task = asyncio.get_event_loop().create_task(self.run_control_loop())

    async def init_flight(self):
        
        while(True):
            try:
                self.flight = await self.api_client.run_full_setup_handshake(self.rocket, self.flight_config.name)
                break
            except:
                self.ui.clear_widgets()
                user_decision_widget = ServerHandshakeDeciderWidget()
                self.ui.add_widget(user_decision_widget)

                user_decision = await user_decision_widget.decision_future

                self.ui.clear_widgets()

                if user_decision == 'CANCEL':
                    return True
                if user_decision == 'RETRY':
                    self.ui.add_widget(Label(text='Retrying to initialize flight'))
                    continue
                
                _, self.flight = to_vessel_and_flight(self.rocket)
                break

        self.realtime_client = RealtimeApiClient(self.api_client, self.flight)
        self.execution_order = topological_sort(self.rocket.parts)

        # Get list of all available measurement sinks
        self.measurement_sinks = [p for p in self.rocket.parts if isinstance(p, MeasurementSinkBase)]

        for p in self.rocket.parts:
            if isinstance(p, ApiMeasurementSinkBase):
                p.api_client = self.api_client
                p.flight = self.flight
        
        return False
    
    async def run_control_loop(self):

        # Before starting the control loop wait for the flight to init
        canceled = await self.init_flight_task

        # Add the part list to the ui
        self.part_list_widget = PartListWidget(self.flight_config.part_uis)
        self.ui.add_widget(self.part_list_widget)

        if canceled:
            return

        # Run the update loop
        flight_loop_iteration = 0
        last_update: float = time.time()
        while True:
            update_end_time = self.control_loop(flight_loop_iteration, last_update)
            self.part_list_widget.update_cur_part()
            flight_loop_iteration += 1
            time_passed = update_end_time - last_update
            last_update = update_end_time

            wait_time = self.max_frame_time - time_passed
            if wait_time < 0:
               continue
        
            # cast(Label, app.label).text = f'Frame Time: {str((time_passed if time_passed > MAX_FRAME_TIME else MAX_FRAME_TIME)*1000)}ms'
            await asyncio.sleep(wait_time)
            # await draw()

    def control_loop(self, iteration: int, last_update: float):

        now = time.time()
        now_datetime = datetime.fromtimestamp(now)

        # Make a list of all new commands sorted by part
        new_commands = self.realtime_client.swap_command_buffer()
        commands_by_part = dict[Part, list[Command]]()
        for c in new_commands:
            part_of_command = self.rocket.part_lookup.get(cast(CommandModel, c)._id)
            if part_of_command is None:
                continue
            if part_of_command not in commands_by_part:
                commands_by_part[part_of_command] = list()
            commands_by_part[part_of_command].append(Command())

        # Call update on every part
        for p in self.execution_order:
            commands = commands_by_part.get(p)
            # Only update if the part is due for update this iteration
            if p.last_update is None or (now - p.last_update) > p.min_update_period.total_seconds():
                try:
                    p.update(commands or [], now, iteration)
                    p.last_update = now
                except:
                    print(f'Iteration {iteration}: Part {p.name} failed to update')

        # Gather all measurements of all parts
        current_measurements = MeasurementsByPart()
        for p in self.execution_order:
            # Only get measurements if the part is due for update this iteration
            if p.last_measurement is None or (now - p.last_measurement) > p.min_measurement_period.total_seconds():
                try:
                    measurements = p.collect_measurements(now, iteration)
                    if measurements is None:
                        continue
                    current_measurements[p] = (p.last_measurement or now, now, measurements)
                    p.last_measurement = now
                except:
                    print(f'Iteration {iteration}: Part {p.name} failed to take measurements')

        # Flush all parts (free memory)
        for p in self.execution_order:
            try:
                p.flush()
            except:
                print(f'Iteration {iteration}: Part {p.name} failed to flush')

        if len(current_measurements) < 1:
            return now

        for sink in self.measurement_sinks:
            sink.measurement_buffer.append(current_measurements)

        return now