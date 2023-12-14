from wizard_step import WizardStep


class WizardStepWizards(WizardStep):
    def __init__(self, config):
        # super(WizardStepButton, self).__init__(config)
        WizardStep.__init__(self, config)
        self.wizards = config.getlists('wizards', [])
        a = ''

def load_config_prefix(config):
    return WizardStepWizards(config)

