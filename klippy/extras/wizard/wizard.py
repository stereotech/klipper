import ast
import json


class Wizard:
    def __init__(self, config):
        if len(config.get_name().split()) > 2:
            raise config.error(
                "Name of section '%s' contains illegal whitespace"
                % (config.get_name()))
        self.name = config.get_name().split()[1]
        self.enabled = False
        self.error = ''
        self.variables = {}
        self._variables_bk = {}
        prefix = 'variable_'
        for option in config.get_prefix_options(prefix):
            try:
                literal = ast.literal_eval(config.get(option))
                json.dumps(literal, separators=(',', ':'))
                self.variables[option[len(prefix):]] = literal
                self._variables_bk[option[len(prefix):]] = literal
            except (SyntaxError, TypeError, ValueError) as e:
                raise config.error(
                    "Option '%s' in section '%s' is not a valid literal: %s" % (
                        option, config.get_name(), e))
        # get options from config
        self.image = config.get('image', '')
        self.type = config.get('type', 'any')
        self.steps = config.getlists('steps', [])
        self.current_step = self.steps[0]
        # load objects
        self.printer = printer = config.get_printer()
        self.gcode = printer.lookup_object('gcode')
        # register commands
        self.gcode.register_mux_command("SET_WIZARD_VARIABLE", "WIZARD",
                                        self.name, self.cmd_SET_WIZARD_VARIABLE,
                                        desc=self.cmd_SET_WIZARD_VARIABLE_help)
        self.gcode.register_mux_command("SET_WIZARD_ENABLE", "WIZARD",
                                        self.name, self.cmd_SET_WIZARD_ENABLE,
                                        desc=self.cmd_SET_WIZARD_ENABLE_help)
        self.gcode.register_mux_command("SET_WIZARD_STEP", "WIZARD",
                                        self.name, self.cmd_SET_WIZARD_STEP,
                                        desc=self.cmd_SET_WIZARD_STEP_help)
        self.gcode.register_mux_command("RESET_WIZARD", "WIZARD",
                                        self.name, self.cmd_RESET_WIZARD,
                                        desc=self.cmd_RESET_WIZARD_help)

    def get_status(self, eventtime=None):
        return {'current_step': self.current_step,
                'enabled': self.enabled,
                'error': self.error,
                'variables': self.variables,
                'name': self.name,
                'steps': self.steps,
                'type': self.type}

    cmd_SET_WIZARD_VARIABLE_help = "Set the value of a wizard variable  to wizard"

    def cmd_SET_WIZARD_VARIABLE(self, gcmd):
        variable = gcmd.get('VARIABLE')
        value = gcmd.get('VALUE')
        if variable not in self.variables:
            raise gcmd.error(
                "2051: Unknown wizard variable '%s'" % (variable,))
        try:
            pass
            literal = ast.literal_eval(value)
            json.dumps(literal, separators=(',', ':'))
        except (SyntaxError, TypeError, ValueError) as e:
            raise gcmd.error("2052: Unable to parse '%s' as a literal: %s" %
                             (value, e))
        v = dict(self.variables)
        v[variable] = literal
        self.variables = v

    cmd_SET_WIZARD_ENABLE_help = "Set the enable to WIZARD"

    def cmd_SET_WIZARD_ENABLE(self, gcmd):
        self.enabled = True if gcmd.get_int('ENABLE', self.enabled) else False
        self.error = gcmd.get('ERROR', self.error)

    cmd_SET_WIZARD_STEP_help = "Set the step to WIZARD"

    def cmd_SET_WIZARD_STEP(self, gcmd):
        step = gcmd.get('STEP')
        if step not in self.steps:
            raise gcmd.error("2053: Unknown step: '%s'" % step)
        self.current_step = step

    cmd_RESET_WIZARD_help = "Reset state the wizard"

    def cmd_RESET_WIZARD(self, gcmd):
        self.error = ''
        self.enabled = False
        self.current_step = self.steps[0]
        self.variables = dict(self._variables_bk)


def load_config_prefix(config):
    return Wizard(config)
