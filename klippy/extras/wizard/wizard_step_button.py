from wizard_step import WizardStep


class WizardStepButton(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        # create template
        self.template_button = self.gcode_macro.load_template(config, 'button_%s_gcode' % self.name)
        # register commands
        self.gcode.register_mux_command("WIZARD_STEP_BUTTON", 'BUTTON',
                                        self.name, self.cmd_WIZARD_STEP_BUTTON,
                                        desc=self.cmd_WIZARD_STEP_BUTTON_help)

    cmd_WIZARD_STEP_BUTTON_help = "Run gcode in the 'button_%s_gcode' section"
    def cmd_WIZARD_STEP_BUTTON(self, gcmd):
        if self.in_script:
            raise gcmd.error("2054: Macro %s called recursively" % (self.name,))
        # update status to the wizard
        wizard_name = gcmd.get('WIZARD').upper()
        wizard_obj = self.printer.lookup_object('wizard %s' % wizard_name)
        kwparams = self.template_action.create_template_context()
        kwparams['wizard'] = wizard_obj.get_status()
        kwparams['wizard'].update({'wizard_step_name': self.name})
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        self.in_script = True
        try:
            self.template_button.run_gcode_from_command(kwparams)
        finally:
            self.in_script = False

def load_config_prefix(config):
    return WizardStepButton(config)
