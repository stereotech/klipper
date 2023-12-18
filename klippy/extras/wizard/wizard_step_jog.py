from wizard_step import WizardStep


class WizardStepJog(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        # get options
        self.axes = config.getlists('axes', ['x', 'y', 'z'])
        self.steps = config.getfloatlist('steps')
        self.default_step = config.getfloat('default_step', 10)
        # create template
        self.template_jog = self.gcode_macro.load_template(config, 'jog_gcode')
        # register gcode commands
        self.gcode.register_mux_command("WIZARD_STEP_JOG", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_JOG,
                                        desc=self.cmd_WIZARD_STEP_JOG_help)
        self.gcode.register_mux_command("WIZARD_STEP_SET_STEP", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_SET_STEP,
                                        desc=self.cmd_WIZARD_STEP_SET_STEP_help)

    cmd_WIZARD_STEP_SET_STEP_help = "Set step for moving the axis"

    def cmd_WIZARD_STEP_SET_STEP(self, gcmd):
        value = gcmd.get_float('VALUE')
        if value not in self.steps:
            raise gcmd.error(
                "2057: error setting the value:%s to move the axis, the value is out of range" % (value,))
        self.default_step = value

    cmd_WIZARD_STEP_JOG_help = "Perform axis movement"

    def cmd_WIZARD_STEP_JOG(self, gcmd):
        axis = gcmd.get('AXIS').lower()
        # get direction move, 1-positive, 0-negative moving
        direction = gcmd.get('DIRECTION', 1)
        if axis not in self.axes:
            raise gcmd.error(
                "2058: error moved the axis:%s, the axis not availability" % (axis,))
        if self.in_script:
            raise gcmd.error(
                "2059: Macro %s called recursively" % (self.name,))
        # update status to the wizard
        wizard_name = gcmd.get('WIZARD').upper()
        wizard_obj = self.printer.lookup_object('wizard %s' % wizard_name)
        kwparams = self.template_action.create_template_context()
        kwparams['wizard'] = wizard_obj.get_status()
        kwparams['wizard'].update({'wizard_step_name': self.name})
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        kwparams['axis'] = axis
        kwparams['step'] = self.default_step
        kwparams['direction'] = direction
        self.in_script = True
        try:
            self.template_jog.run_gcode_from_command(kwparams)
        finally:
            self.in_script = False

    def get_status(self, eventtime):
        return {'step': self.default_step}


def load_config_prefix(config):
    return WizardStepJog(config)
