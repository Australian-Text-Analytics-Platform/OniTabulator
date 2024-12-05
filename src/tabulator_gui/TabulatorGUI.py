import panel as pn
from panel import Column
from panel.theme import Fast
from panel.viewable import Viewer, Viewable

pn.extension(notifications=True, design=Fast)


class TabulatorGUI(Viewer):
    def __init__(self, **params):
        super().__init__(**params)
        self.panel = Column()

    def __panel__(self) -> Viewable:
        return self.panel
