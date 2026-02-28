"""
GUIPanel base class.
Every panel implements build() and refresh().
"""

from abc import ABC, abstractmethod


class GUIPanel(ABC):
    name:   str
    title:  str
    active: bool = True

    @abstractmethod
    def build(self, container) -> None:
        """Mount all NiceGUI elements into container. Called once at startup."""
        ...

    @abstractmethod
    def refresh(self, state: dict) -> None:
        """
        Called on every timer tick with the latest system_state snapshot.
        Must never block. Must never call queue.get() — read only from state dict.
        """
        ...
