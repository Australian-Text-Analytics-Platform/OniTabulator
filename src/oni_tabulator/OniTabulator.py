import json
import re
import urllib
from contextlib import contextmanager
from io import StringIO
from os import makedirs
from pathlib import Path

import panel
import panel as pn
from panel import Column, Row
from panel.layout import Divider
from panel.theme import Fast
from panel.viewable import Viewer, Viewable
from panel.widgets import Select, TextInput, PasswordInput, Button, JSONEditor

from rocrate_tabular.tabulator import ROCrateTabulator, ROCrateTabulatorException

pn.extension('ace', 'jsoneditor', notifications=True, design=Fast)


class OniTabulator(Viewer):
    STANDARD_WIDTH: int = 150
    DEFAULT_PROVIDER: str = "https://data.ldaca.edu.au"
    DATA_PATH: Path = Path(__file__).parent.parent / 'data'

    def __init__(self, **params):
        super().__init__(**params)
        makedirs(self.DATA_PATH, exist_ok=True)
        self.tabulator = ROCrateTabulator()

        self.provider_selector = Select(name='Provider selector', options=[self.DEFAULT_PROVIDER], width=self.STANDARD_WIDTH)
        self.custom_provider_input = TextInput(name='Add custom provider', width=self.STANDARD_WIDTH)

        self.api_key_input = PasswordInput(name='API Key', placeholder='af6391e0-f873-11ee-8355-bae397411a92')

        self.collection_id_input = TextInput(name='Collection ID', placeholder='arcp://name,doi10.26180%2F23961609')
        self.retrieve_collection_button = Button(name='Retrieve collection', align='end',
                                                 button_type='success', button_style='solid')
        self.get_table_parameters_button = Button(name='Get parameters', align='start',
                                                  button_type='primary', button_style='solid')

        self.config_editor = JSONEditor()
        self.loading_indicator = pn.indicators.LoadingSpinner(name='', size=50, value=False, visible=False)

        self.panel = Column(
            Row(self.provider_selector, self.custom_provider_input, self.loading_indicator),
            self.api_key_input,
            Row(self.collection_id_input, self.retrieve_collection_button),
            Divider(),
            Row(self.config_editor, self.get_table_parameters_button),
            min_width=700
        )

        self.custom_provider_input.param.watch(self._add_custom_provider, ['value'])
        self.retrieve_collection_button.on_click(self._retrieve_collection_information)
        self.get_table_parameters_button.on_click(self._get_table_parameters)

    def __panel__(self) -> Viewable:
        return self.panel

    @contextmanager
    def loading(self, loading_msg: str = ""):
        self.loading_indicator.name = loading_msg
        self.loading_indicator.value = True
        self.loading_indicator.visible = True
        try:
            yield
        finally:
            self.loading_indicator.name = ""
            self.loading_indicator.value = False
            self.loading_indicator.visible = False

    def _add_custom_provider(self, event):
        new_provider: str = event.new
        if new_provider in self.provider_selector.options:
            self.custom_provider_input.value = ''
            return
        if len(new_provider) == 0:
            return
        self.provider_selector.options = self.provider_selector.options + [new_provider]
        self.provider_selector.value = new_provider
        self.custom_provider_input.value = ''

    def _write_crate_to_db(self):
        collection_id: str = self.collection_id_input.value.rstrip()
        db_file_name = self._url_to_filename(collection_id) + '.db'
        db_path = self.DATA_PATH / db_file_name

        collection_url = self._construct_collection_url()
        try:
            self.tabulator.crate_to_db(collection_url, db_path)
        except ROCrateTabulatorException as e:
            panel.state.notifications.error(str(e))

    def _retrieve_collection_information(self, *_):
        with self.loading("Retrieving collection info..."):
            self._write_crate_to_db()

            self.tabulator.infer_config()
            config_fobj = StringIO()
            self.tabulator.write_config(config_fobj)
            self.config_editor.value = json.load(config_fobj)

    def _get_table_parameters(self, *_):
        with self.loading("Obtaining parameters..."):
            curr_config = self.config_editor.value
            if len(curr_config):
                config_fobj = StringIO()
                json.dump(curr_config, config_fobj)
                self.tabulator.load_config(config_fobj)
            else:
                self.tabulator.infer_config()
            for table in self.tabulator.cf["tables"]:
                self.tabulator.entity_table(table, None)

            self._write_crate_to_db()

            config_fobj = StringIO()
            self.tabulator.write_config(config_fobj)
            self.config_editor.value = json.load(config_fobj)

    def _construct_collection_url(self) -> str:
        provider: str = self.provider_selector.value
        collection_id: str = self.collection_id_input.value
        collection_id = collection_id.rstrip()

        return f"{provider}/api/object/meta?id={collection_id}&noUrid&resolve-parts"

    def _url_to_filename(self, url: str) -> str:
        max_length = 200
        parsed_url = urllib.parse.unquote(url)
        clean_url = re.sub(r'[:/\\?&=#%]+', '_', parsed_url)

        return clean_url[:max_length]


if __name__ == "__main__":
    pn.serve(OniTabulator())
