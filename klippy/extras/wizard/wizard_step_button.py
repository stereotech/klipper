from wizard_step import WizardStep


class WizardStepButton(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        # create template for buttons
        self.templates = {}
        options_name = config.get_prefix_options('button_')
        for option in options_name:
            template_button = self.gcode_macro.load_template(
                config, option)
            button_name = '_'.join(option.split('_')[1:-1])
            self.templates.update({button_name: template_button})
        # register commands
        self.gcode.register_mux_command("WIZARD_STEP_BUTTON", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_BUTTON,
                                        desc=self.cmd_WIZARD_STEP_BUTTON_help)

    cmd_WIZARD_STEP_BUTTON_help = "Run gcode in the 'button_%s_gcode' section"

    def cmd_WIZARD_STEP_BUTTON(self, gcmd):
        if self.in_script:
            raise gcmd.error(
                "2054: Macro %s called recursively" % (self.name,))
        wizard_name = gcmd.get('WIZARD').upper()
        wizard_obj = self.printer.lookup_object('wizard %s' % wizard_name)
        button = gcmd.get('BUTTON', '').lower()
        template_button = self.templates.get(button, None)
        if template_button is None:
            raise gcmd.error(
                "2060: The button '%s' does not exist" % (button,))
        kwparams = template_button.create_template_context()
        kwparams['wizard'] = wizard_obj.get_status()
        kwparams['wizard'].update({'wizard_step_name': self.name})
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        self.in_script = True
        try:
            template_button.run_gcode_from_command(kwparams)
        finally:
            self.in_script = False

    def get_status(self, eventtime):
        status = WizardStep.get_status(self, eventtime)
        return status


def load_config_prefix(config):
    return WizardStepButton(config)
