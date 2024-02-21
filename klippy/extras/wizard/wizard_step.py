class WizardStep:
    def __init__(self, config):
        if len(config.get_name().split()) > 2:
            raise config.error(
                "Name of section '%s' contains illegal whitespace"
                % (config.get_name()))
        section_name = config.get_name().split()
        self.name = section_name[1].upper()
        self.in_script = False
        self.loading = False
        # load objects
        self.printer = printer = config.get_printer()
        self.gcode_macro = printer.load_object(config, 'gcode_macro')
        self.gcode = printer.lookup_object('gcode')
        # get options from config
        self.cmd_desc = config.get("description", '')
        self.image = config.get('image', '')
        self.landscape = config.getboolean('landscape', False)
        self.description = config.get('description', '')
        self.warning = config.get('warning', '')
        self.info = config.get('info', '')
        self.countdown = config.getint('countdown', 0)
        self.placeholder = config.get('placeholder', '')
        # create template
        self.template_action = self.gcode_macro.load_template(
            config, 'action_gcode')
        self.template_cancel = self.gcode_macro.load_template(
            config, 'cancel_gcode')
        # register gcode commands
        self.gcode.register_mux_command("WIZARD_STEP_LOADING_STATE", 'STEP',
                                        self.name, self.cmd_WIZARD_STEP_LOADING_STATE,
                                        desc=self.cmd_WIZARD_STEP_LOADING_STATE_help)
        self.gcode.register_mux_command("EXECUTE_WIZARD_STEP", 'STEP',
                                        self.name, self.cmd_EXECUTE_WIZARD_STEP,
                                        desc=self.cmd_EXECUTE_WIZARD_STEP_help)
        self.gcode.register_mux_command("CANCEL_WIZARD_STEP", 'STEP',
                                        self.name, self.cmd_CANCEL_WIZARD_STEP,
                                        desc=self.cmd_CANCEL_WIZARD_STEP_help)

    cmd_WIZARD_STEP_LOADING_STATE_help = "Change state for show the placeholder"

    def cmd_WIZARD_STEP_LOADING_STATE(self, gcmd):
        state = gcmd.get_int('ENABLE', 0)
        self.loading = True if state else False

    cmd_EXECUTE_WIZARD_STEP_help = "Run gcode in the 'action_gcode' option"

    def cmd_EXECUTE_WIZARD_STEP(self, gcmd):
        self.cmd(gcmd=gcmd, gcode='action_gcode')

    cmd_CANCEL_WIZARD_STEP_help = "Run gcode in the 'cancel_gcode' option"

    def cmd_CANCEL_WIZARD_STEP(self, gcmd):
        self.cmd(gcmd=gcmd, gcode='cancel_gcode')

    def cmd(self, gcmd, gcode):
        if self.in_script:
            raise gcmd.error(
                "2054: Macro %s called recursively" % (self.name,))
        wizard_name = gcmd.get('WIZARD').upper()
        wizard_obj = self.printer.lookup_object('wizard %s' % wizard_name)
        kwparams = self.template_action.create_template_context()
        kwparams['wizard'] = wizard_obj.get_status()
        kwparams['wizard'].update({'wizard_step_name': self.name})
        kwparams['params'] = gcmd.get_command_parameters()
        kwparams['rawparams'] = gcmd.get_raw_command_parameters()
        self.in_script = True
        try:
            if gcode == 'action_gcode':
                kwparams['wizard']['next_step'] = self.get_next_step(kwparams)
                self.template_action.run_gcode_from_command(kwparams)
            elif gcode == 'cancel_gcode':
                self.template_cancel.run_gcode_from_command(kwparams)
        finally:
            self.in_script = False

    def get_next_step(self, kwparams):
        steps =  kwparams['wizard']['steps']
        if self.name == steps[-1]:
            next_step = steps[0]
        else:
            current_step_idx = steps.index(self.name)
            next_step = steps[current_step_idx + 1]
        return next_step

    def get_status(self, eventtime):
        return {
            'loading': self.loading,
            'placeholder': self.placeholder}


def load_config_prefix(config):
    return WizardStep(config)
