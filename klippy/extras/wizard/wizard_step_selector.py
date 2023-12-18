from wizard_step import WizardStep


class WizardStepSelector(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        self.selected = ''
        # get options
        self.items = config.getlists('items', [])
        # create template
        self.template = self.gcode_macro.load_template(config, 'select_gcode')
        # register commands
        self.gcode.register_mux_command("WIZARD_STEP_SELECT", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_SELECT,
                                        desc=self.cmd_WIZARD_STEP_SELECT_help)

    cmd_WIZARD_STEP_SELECT_help = "Run gcode in the 'select_gcode' section"

    def cmd_WIZARD_STEP_SELECT(self, gcmd):
        if self.in_script:
            raise gcmd.error(
                "2054: Macro %s called recursively" % (self.name,))
        selected = gcmd.get('ITEM')
        if selected not in self.items:
            raise gcmd.error(
                "2056: The selected item %s not in the items %s" % (selected, self.items))
        self.selected = selected
        wizard_name = gcmd.get('WIZARD').upper()
        wizard_obj = self.printer.lookup_object('wizard %s' % wizard_name)
        kwparams = self.template_action.create_template_context()
        kwparams['wizard'] = wizard_obj.get_status()
        kwparams['wizard'].update({'wizard_step_name': self.name})
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        kwparams['selected'] = self.selected
        self.in_script = True
        try:
            self.template.run_gcode_from_command(kwparams)
        finally:
            self.in_script = False

    def get_status(self, eventtime):
        return {'selected': self.selected
                }


def load_config_prefix(config):
    return WizardStepSelector(config)
