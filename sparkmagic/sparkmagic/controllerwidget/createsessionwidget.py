# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.
import json

import sparkmagic.utils.configuration as conf
from sparkmagic.utils.constants import LANG_SCALA, LANG_PYTHON, LANG_PYTHON3
from sparkmagic.controllerwidget.abstractmenuwidget import AbstractMenuWidget

import json
import os.path
import re
import ipykernel
import requests

# try:  # Python 3
#    from urllib.parse import urljoin
# except ImportError:  # Python 2
#    from urlparse import urljoin

# Alternative that works for both Python 2 and 3:
from requests.compat import urljoin

try:  # Python 3 (see Edit2 below for why this may not work in Python 2)
    from notebook.notebookapp import list_running_servers
except ImportError:  # Python 2
    import warnings
    from IPython.utils.shimmodule import ShimWarning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ShimWarning)
        from IPython.html.notebookapp import list_running_servers


def get_notebook_name():
    """
    Return the full path of the jupyter notebook.
    """
    kernel_id = re.search('kernel-(.*).json',
                          ipykernel.connect.get_connection_file()).group(1)
    servers = list_running_servers()
    for ss in servers:
        response = requests.get(urljoin(ss['url'], 'api/sessions'),
                                params={'token': ss.get('token', '')})
        for nn in json.loads(response.text):
            if nn['kernel']['id'] == kernel_id:
                return nn['notebook']['path']


class CreateSessionWidget(AbstractMenuWidget):
    def __init__(self, spark_controller, ipywidget_factory, ipython_display, endpoints_dropdown_widget, refresh_method):
        # This is nested
        super(CreateSessionWidget, self).__init__(
            spark_controller, ipywidget_factory, ipython_display, True)

        self.refresh_method = refresh_method

        self.endpoints_dropdown_widget = endpoints_dropdown_widget

        self.session_widget = self.ipywidget_factory.get_text(
            description='Name:',
            value='session-name'
        )
        self.lang_widget = self.ipywidget_factory.get_toggle_buttons(
            description='Language:',
            options=[LANG_SCALA, LANG_PYTHON, LANG_PYTHON3],
        )
        self.properties = self.ipywidget_factory.get_text(
            description='Properties:',
            value=json.dumps(conf.session_configs())
        )
        self.submit_widget = self.ipywidget_factory.get_submit_button(
            description='Create Session'
        )

        self.children = [self.ipywidget_factory.get_html(value="<br/>", width="600px"), self.endpoints_dropdown_widget,
                         self.session_widget, self.lang_widget, self.properties,
                         self.ipywidget_factory.get_html(value="<br/>", width="600px"), self.submit_widget]

        for child in self.children:
            child.parent_widget = self

    def run(self):
        try:
            properties_json = self.properties.value
            if properties_json.strip() != "":
                conf.override(conf.session_configs.__name__,
                              json.loads(self.properties.value))
        except ValueError as e:
            self.ipython_display.send_error(
                "Session properties must be a valid JSON string. Error:\n{}".format(e))
            return

        endpoint = self.endpoints_dropdown_widget.value
        language = self.lang_widget.value
        alias = self.session_widget.value
        skip = False
        properties = conf.get_session_properties(language)
        properties['name'] = get_notebook_name()

        try:
            self.spark_controller.add_session(
                alias, endpoint, skip, properties)
        except ValueError as e:
            self.ipython_display.send_error("""Could not add session with
name:
    {}
properties:
    {}

due to error: '{}'""".format(alias, properties, e))
            return

        self.refresh_method()
