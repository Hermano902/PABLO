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

    def refresh(self, state: dict) -> None:
        """
        Called on every timer tick with the latest system state snapshot.
        Override only if the panel uses imperative (non-refreshable) updates.
        Must never block.
        """
        pass
