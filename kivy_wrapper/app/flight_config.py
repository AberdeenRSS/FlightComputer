from dataclasses import dataclass
from typing import Iterable
from core.logic.rocket_definition import Part, Rocket
from kivy_wrapper.app.ui.default_part_ui import DefaultPartUI
from kivy_wrapper.app.ui.part_ui import PartUi

@dataclass
class FlightConfig():
    '''
    Configuration to start a flight within the app. Includes the rocket specification as well as
    other relevant ui configuration for the flight
    ''' 

    rocket: Rocket


    part_uis: Iterable[PartUi]

    should_add_default_uis: bool
    '''If true adds default UIs for every part. These default UI's display the part's measurements'''

    name: str = ''

    auth_code: str = ''

    def add_default_uis(self):

        new_uis = [*self.part_uis]

        for part in self.rocket.parts:
            new_uis.append(DefaultPartUI(part))

        self.part_uis = new_uis
