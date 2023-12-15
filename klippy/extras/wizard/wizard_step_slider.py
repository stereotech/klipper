from wizard_step import WizardStep


class WizardStepSlider(WizardStep):
    def __init__(self, config):
        # super(WizardStepButton, self).__init__(config)
        WizardStep.__init__(self, config)
        self.slider_data = {}
        options = config.get_prefix_options('slider')
        for option in options:
            self.slider_data.update({option: config.getint(option)})
        self.gcode.register_mux_command("WIZARD_STEP_SLIDER", 'SLIDER',
                                        self.name, self.cmd_WIZARD_STEP_SLIDER,
                                        desc=self.cmd_WIZARD_STEP_SLIDER_help)

    cmd_WIZARD_STEP_SLIDER_help = "update value to the slider data"
    def cmd_WIZARD_STEP_SLIDER(self, gcmd):
        variable = gcmd.get('VARIABLE').lower()
        value = gcmd.get_int('VALUE')
        if variable not in self.slider_data:
            raise gcmd.error("failure set value:%s to variable:%s in the slider %s" % (value, variable, self.name))
        self.slider_data.update({variable: value})

    def get_status(self, eventtime):
        return self.slider_data

def load_config_prefix(config):
    return WizardStepSlider(config)

