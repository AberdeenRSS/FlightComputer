

from typing import Generic, TypeVar
from app.logic.rocket_definition import Part

T = TypeVar('T', bound=Part)

class PartUi(Generic[T]):

    # Name displayed to the user where they can choose which part to look at
    name: str

    # The part that this widget represents
    part: T

    # Called on every iteration. Update ui for the component here
    def draw(self):
        pass
