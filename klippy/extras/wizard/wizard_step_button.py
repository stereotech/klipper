from wizard_step import WizardStep


class WizardStepButton(WizardStep):
    def __init__(self, config):
        # super(WizardStepButton, self).__init__(config)
        WizardStep.__init__(self, config)
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.template = gcode_macro.load_template(config, 'button_%s_gcode' % self.name)
        self.gcode.register_mux_command("WIZARD_STEP_BUTTON", 'BUTTON',
                                        self.name, self.cmd_WIZARD_STEP_BUTTON,
                                        desc=self.cmd_WIZARD_STEP_BUTTON_help)

    cmd_WIZARD_STEP_BUTTON_help = "Run gcode in the 'button_%s_gcode' section"
    def cmd_WIZARD_STEP_BUTTON(self, gcmd):
        if self.in_script:
            raise gcmd.error("Macro %s called recursively" % (self.name,))
        # update status to the wizard
        wizard_name = gcmd.get('WIZARD')
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
            self.template.run_gcode_from_command(kwparams)
        finally:
            # self.template_cancel.run_gcode_from_command(kwparams)
            self.in_script = False

def load_config_prefix(config):
    return WizardStepButton(config)

