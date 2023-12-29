from wizard_step import WizardStep


OPTIONS = {
    'min': 0,
    'max': 100,
    'step': 1,
    'default': 20,
}

class WizardStepSlider(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        # get slider options from config
        self.slider_data = {}
        options = config.get_prefix_options('slider_')
        sliders = {'_'.join(option.split('_')[1:-1]) for option in options}
        for slider in sliders:
            self.slider_data.update({slider: {}})
            for key, value in OPTIONS.items():
                option_name = 'slider_%s_%s' % (slider, key)
                config_value = config.getfloat(option_name, value)
                self.slider_data[slider].update({option_name: config_value})
                if 'default' in option_name:
                    self.slider_data[slider].update({'current_value': config_value})
        self.gcode.register_mux_command("WIZARD_STEP_SLIDER", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_SLIDER,
                                        desc=self.cmd_WIZARD_STEP_SLIDER_help)

    cmd_WIZARD_STEP_SLIDER_help = "update value to the slider data"

    def cmd_WIZARD_STEP_SLIDER(self, gcmd):
        slider = gcmd.get('SLIDER')
        value = gcmd.get_float('VALUE')
        if slider not in self.slider_data:
            raise gcmd.error("2055: Failure set value:%s to slider:%s" % (value, slider))
        self.slider_data[slider].update({'current_value': value})

    def get_status(self, eventtime):
        return {slider: value['current_value'] for slider, value in self.slider_data.items()}


def load_config_prefix(config):
    return WizardStepSlider(config)
