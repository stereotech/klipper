from . import wizard,\
              wizard_step,\
              wizard_step_button,\
              wizard_step_wizards,\
              wizard_step_selectors, \
              wizard_step_slider, \
              wizard_step_jog


def load_config_prefix(config):
    name = config.get_name()
    if 'wizard_step ' in name:
        return wizard_step.load_config_prefix(config)
    elif 'wizard ' in name:
        return wizard.load_config_prefix(config)
    elif 'wizard_step_button ' in name:
        return wizard_step_button.load_config_prefix(config)
    elif 'wizard_step_wizards ' in name:
        return wizard_step_wizards.load_config_prefix(config)
    elif 'wizard_step_selectors ' in name:
        return wizard_step_selectors.load_config_prefix(config)
    elif 'wizard_step_slider ' in name:
        return wizard_step_slider.load_config_prefix(config)
    elif 'wizard_step_jog ' in name:
        return wizard_step_jog.load_config_prefix(config)
    else:
        raise config.error(
            "do not parse section: %s" % name)
