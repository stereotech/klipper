from wizard_step import WizardStep


class WizardStepWizards(WizardStep):
    def __init__(self, config):
        WizardStep.__init__(self, config)
        self.wizards = config.getlists('wizards', [])

def load_config_prefix(config):
    return WizardStepWizards(config)
