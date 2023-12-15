import traceback, logging, ast, copy, json
import jinja2


class WizardStep:
    def __init__(self, config):
        if len(config.get_name().split()) > 2:
            raise config.error(
                    "Name of section '%s' contains illegal whitespace"
                    % (config.get_name()))
        section_name = config.get_name().split()
        self.name = section_name[1].upper()
        self.in_script = False
        # load objects
        self.printer = printer = config.get_printer()
        self.gcode_macro = printer.load_object(config, 'gcode_macro')
        self.gcode = printer.lookup_object('gcode')
        # create template
        self.template_action = self.gcode_macro.load_template(config, 'action_gcode')
        self.template_cancel = self.gcode_macro.load_template(config, 'cancel_gcode')
        # get params from config
        self.cmd_desc = config.get("description", "G-Code wizard")
        self.image = config.get('image', 'image_path')
        self.landscape = config.getboolean('landscape', False)
        self.description = config.get('description', '')
        self.warning = config.get('warning', '')
        self.info = config.get('info', '')
        self.countdown = config.getint('countdown', 0)
        # register gcode commands
        key = 'STEP'
        # key = full_name[0].split('_')[-1].upper()
        self.gcode.register_mux_command("EXECUTE_WIZARD_STEP", key,
                                        self.name, self.cmd_EXECUTE_WIZARD_STEP,
                                        desc=self.cmd_EXECUTE_WIZARD_STEP_help)
        self.gcode.register_mux_command("CANCEL_WIZARD_STEP", key,
                                        self.name, self.cmd_CANCEL_WIZARD_STEP,
                                        desc=self.cmd_CANCEL_WIZARD_STEP_help)
        # self.gcode.register_command(self.alias, self.cmd,
        #                             desc=self.cmd_desc)



    cmd_EXECUTE_WIZARD_STEP_help = "Run gcode in the 'action_gcode' section"
    def cmd_EXECUTE_WIZARD_STEP(self, gcmd):
        self.cmd(gcmd=gcmd, gcode='action_gcode')

    cmd_CANCEL_WIZARD_STEP_help = "Run gcode in the 'cancel_gcode' section"
    def cmd_CANCEL_WIZARD_STEP(self, gcmd):
        self.cmd(gcmd=gcmd, gcode='cancel_gcode')

    def cmd(self, gcmd, gcode):
        if self.in_script:
            raise gcmd.error("Macro %s called recursively" % (self.name,))
        # update status to the wizard
        wizard_name = gcmd.get('WIZARD').upper()
        wizard_obj = self.printer.lookup_object('wizard %s' % wizard_name)
        wizard_obj.update_status(current_step=self.name)
        # kwparams = {}
        kwparams = dict(wizard_obj.variables)
        kwparams.update(self.template_action.create_template_context())
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        kwparams['wizard'] = wizard_name
        self.in_script = True
        try:
            if gcode == 'action_gcode':
                self.template_action.run_gcode_from_command(kwparams)
            elif gcode == 'cancel_gcode':
                self.template_cancel.run_gcode_from_command(kwparams)
        finally:
            # self.template_cancel.run_gcode_from_command(kwparams)
            self.in_script = False


def load_config_prefix(config):
    return WizardStep(config)

