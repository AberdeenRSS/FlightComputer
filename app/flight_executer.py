import asyncio
import time
from typing import Collection, Iterable, cast
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from app.api_client import ApiClient, RealtimeApiClient
from app.flight_config import FlightConfig
from app.logic.commands.command import Command, Command
from app.logic.commands.command_helper import deserialize_command, gather_known_commands, make_command_schemas
from app.logic.to_vessel_and_flight import to_vessel_and_flight
from app.models.command import Command as CommandModel, CommandSchema
from app.logic.execution import topological_sort
from app.logic.measurement_sink import ApiMeasurementSinkBase, MeasurementSinkBase, MeasurementsByPart
from app.logic.rocket_definition import Part, Rocket
from app.ui.part_ui import PartUi

class FlightExecuterUI(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_widget(Label(text='Initializing Flight'))

class ServerHandshakeDeciderWidget(BoxLayout):

    def __init__(self, exception, **kwargs):
        kwargs['orientation'] = 'vertical'
        super().__init__(**kwargs)

        self.decision_future = asyncio.Future()

        self.add_widget(Label(text=f'Server Handshake failed: {exception}', size_hint=(1, 0.25)))

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

    known_commands: dict[str, type[Command]]
    '''
    List of commands known within the context of the flight. Used to
    initialize the actual command objects from the models send by the 
    server
    '''

    executed_commands: list[Command]

    def __init__(self, flight_config: FlightConfig, max_frame_time: float = 0.001) -> None:
    
        self.executed_commands = list()

        self.flight_config = flight_config
        self.rocket = flight_config.rocket
        self.max_frame_time = max_frame_time

        self.execution_order = topological_sort(self.rocket.parts)
        self.known_commands = gather_known_commands(self.rocket)
        self.command_schemas = make_command_schemas(self.known_commands)

        self.api_client = ApiClient()
        self.ui = FlightExecuterUI()

        self.init_flight_task = asyncio.get_event_loop().create_task(self.init_flight())
        self.control_loop_task = asyncio.get_event_loop().create_task(self.run_control_loop())

        self.send_command_responses_task = asyncio.get_event_loop().create_task(self.send_command_responses())

    async def init_flight(self):
        
        while(True):
            try:
                self.flight = await self.api_client.run_full_setup_handshake(self.rocket, self.flight_config.name)

                self.realtime_client = RealtimeApiClient(self.api_client, self.flight)
                self.realtime_client.connect()

                break
            except Exception as e:

                print(f'Failed connecting to server: {e}')

                self.ui.clear_widgets()
                user_decision_widget = ServerHandshakeDeciderWidget(e)
                self.ui.add_widget(user_decision_widget)

                user_decision = await user_decision_widget.decision_future

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
        new_commands = [deserialize_command(self.known_commands, c) for c in self.realtime_client.swap_command_buffer()] if self.realtime_client is not None else []
        commands_by_part = dict[Part, list[Command]]()
        self.add_command_by_part(new_commands, commands_by_part)

        # Call update on every part
        for p in self.execution_order:
            commands = commands_by_part.get(p)
            # Only update if the part is due for update this iteration or if there are commands for it
            if (p not in commands_by_part) and (p.last_update is not None) and ((now - p.last_update) < p.min_update_period.total_seconds()):
                continue
            try:
                generated_commands = p.update(commands or [], now, iteration)
                if generated_commands is not None:
                    new_commands.extend(generated_commands)
                    self.add_command_by_part(generated_commands, commands_by_part)
                p.last_update = now
            except:
                print(f'Iteration {iteration}: Part {p.name} failed to update')

        # Gather all measurements of all parts
        current_measurements = MeasurementsByPart()
        for p in self.execution_order:
            # Only get measurements if the part is due for update this iteration or if there was a command for the part
            if (p not in commands_by_part) and (p.last_measurement is not None) and ((now - p.last_measurement) < p.min_measurement_period.total_seconds()):
                continue
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

        self.executed_commands.extend(new_commands)

        return now

    def add_command_by_part(self, new_commands: Collection[Command], commands_by_part: dict[Part, list[Command]]):
        for c in new_commands:

            if c._part_id is None:
                continue

            part_of_command = self.rocket.part_lookup.get(c._part_id)
            if part_of_command is None:
                continue
            if part_of_command not in commands_by_part:
                commands_by_part[part_of_command] = list()
            commands_by_part[part_of_command].append(c)
    
    async def send_command_responses(self):

        abort = await self.init_flight_task

        if(abort):
            return

        while(True):

            if len(self.executed_commands) < 1:
                await asyncio.sleep(0.01)
                continue

            # swap buffer
            commands_to_send = self.executed_commands
            self.executed_commands = list()

            # Set all commands to failed, if they haven't been processed yet
            for c in commands_to_send:
                if c.state == 'dispatched' or c.state == 'received':
                    c.state = 'failed'

            c_schema = CommandSchema()

            # Convert the commands into native objects (ready to be send over the api)
            models = [ (self.command_schemas.get(c.command_type) or c_schema).dump(c) for c in commands_to_send ]

            try:
                await self.api_client.try_send_command_responses(str(self.flight._id), models)
            except Exception as e:
                print(f'Failed sending {len(models)} command responses: {e}')

    def __del__(self):

        if not self.control_loop_task.done():
            self.control_loop_task.cancel()

        if not self.init_flight_task.done():
            self.init_flight_task.cancel()

        if not self.send_command_responses_task.done():
            self.send_command_responses_task.cancel()
