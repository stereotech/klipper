import traceback, logging, ast, copy, json
import jinja2


class WizardStep:
    def __init__(self, config):
        if len(config.get_name().split()) > 2:
            raise config.error(
                    "Name of section '%s' contains illegal whitespace"
                    % (config.get_name()))
        name = config.get_name().split()[1]
        self.alias = name.upper()
        self.printer = printer = config.get_printer()
        gcode_macro = printer.load_object(config, 'gcode_macro')
        self.template_action = gcode_macro.load_template(config, 'action_gcode')
        self.template_cancel = gcode_macro.load_template(config, 'cancel_gcode')
        self.gcode = printer.lookup_object('gcode')
        self.cmd_desc = config.get("description", "G-Code macro")
        self.gcode.register_command(self.alias, self.cmd,
                                    desc=self.cmd_desc)
        self.gcode.register_mux_command("EXECUTE_WIZARD_STEP", "STEP",
                                        name, self.cmd_EXECUTE_WIZARD_STEP,
                                        desc=self.cmd_EXECUTE_WIZARD_STEP_help)
        self.gcode.register_mux_command("CANCEL_WIZARD_STEP", "STEP",
                                        name, self.cmd_CANCEL_WIZARD_STEP,
                                        desc=self.cmd_CANCEL_WIZARD_STEP_help)
        self.in_script = False

        self.image = config.get('image', 'image_path')
        self.landscape = config.getboolean('landscape', False)
        self.description = config.get('description', '')
        self.warning = config.get('warning', '')
        self.info = config.get('info', '')
        self.countdown = config.getint('countdown', 0)

    cmd_EXECUTE_WIZARD_STEP_help = "Set the enable to WIZARD"
    def cmd_EXECUTE_WIZARD_STEP(self, gcmd):
        gcmd.respond_info('-----EXECUTE_WIZARD_STEP')

    cmd_CANCEL_WIZARD_STEP_help = "Set the step to WIZARD"
    def cmd_CANCEL_WIZARD_STEP(self, gcmd):
        gcmd.respond_info('-----EXECUTE_WIZARD_STEP')

    def cmd(self, gcmd):
        if self.in_script:
            raise gcmd.error("Macro %s called recursively" % (self.alias,))
        kwparams = {}
        kwparams.update(self.template_action.create_template_context())
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        self.in_script = True
        try:
            self.template_action.run_gcode_from_command(kwparams)
        finally:
            self.template_cancel.run_gcode_from_command(kwparams)
            self.in_script = False

def load_config_prefix(config):
    return WizardStep(config)

