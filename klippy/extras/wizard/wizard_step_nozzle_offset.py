from wizard_step import WizardStep


class WizardStepNozzleOffset(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        # get options from config
        self.step_x = self.step_y = config.getint('default_step', 7)
        self.quantity_steps = config.getint('steps', 15)
        self.step_value = config.getfloat('step_value', 0.1)
        self.min_value = -config.getfloat('min_value', -0.7)
        self.gcode.register_mux_command("WIZARD_STEP_NOZZLE_OFFSET", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_NOZZLE_OFFSET,
                                        desc=self.cmd_WIZARD_STEP_NOZZLE_OFFSET_help)

    cmd_WIZARD_STEP_NOZZLE_OFFSET_help = "update value to the slider data"

    def cmd_WIZARD_STEP_NOZZLE_OFFSET(self, gcmd):
        step_x = gcmd.get_int('STEP_X', self.step_x)
        step_y = gcmd.get_int('STEP_Y', self.step_y)
        if min(step_x, step_y) < 0 or max(step_x, step_y) > self.quantity_steps:
            raise gcmd.error(
                "2060: Failure set value to step, value out of the range[0-%s]" % (self.quantity_steps))
        self.step_x = step_x
        self.step_y = step_y

    def get_status(self, eventtime):
        return {
            'step_x': self.step_x,
            'step_y': self.step_y,
            }


def load_config_prefix(config):
    return WizardStepNozzleOffset(config)
