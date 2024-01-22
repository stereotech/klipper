from wizard_step import WizardStep
import os
import json


class WizardStepTree(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        self.tree = []
        self.selected = ''
        self.value = 0
        # get options from config
        self.depth = config.getint('depth', 1)
        self.types = config.getlist('types', [])
        path = config.get('tree_file_path', '')
        filename = os.path.abspath(path)
        if os.path.isfile(filename):
            try:
                with open(filename, 'r') as f:
                    self.tree = json.load(f)
            except Exception as e:
                raise config.error("0026: do not parse .json file, error %s" % e)
        else:
            raise config.error("0026: file with data not exist")
        # register commands
        self.gcode.register_mux_command("WIZARD_STEP_TREE", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_TREE,
                                        desc=self.cmd_WIZARD_STEP_TREE_help)

    cmd_WIZARD_STEP_TREE_help = "select key from tree for set the value"

    def cmd_WIZARD_STEP_TREE(self, gcmd):
        selected = gcmd.get('KEY')
        value = self.get_value(self.tree, selected)
        if value:
            self.value = value
            self.selected = selected
        else:
            raise gcmd.error(
                "2062: the key does not exist - %s, check the key" % (selected,))

    def get_value(self, node, key):
        if isinstance(node, list):
            for item in node:
                value = self.get_value(item, key)
                if isinstance(value, int):
                    return value
        elif isinstance(node, dict):
            if node.get('key', '') == key:
                return node['value']
            if node.get('children', ''):
                for child in node['children']:
                    value = self.get_value(child, key)
                    if isinstance(value, int):
                        return value

    def get_status(self, eventtime):
        return {
            'tree': self.tree,
            'selected': self.selected,
            'value': self.value
        }


def load_config_prefix(config):
    return WizardStepTree(config)
