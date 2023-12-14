# Package definition for the extras/display directory
#
# Copyright (C) 2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from . import wizard, wizard_step, wizard_step_button, wizard_step_wizards, wizard_step_selectors

# def load_config(config):
#     return wizard.load_config(config)

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
    else:
        raise config.error(
            "do not parse section: %s" % name)
    # elif config.has_section('wizard_step_slider'):
    #     raise config.error(
    #         "0018: A primary [display] section must be defined in printer.cfg "
    #         "to use auxilary displays")
    # name = config.get_name().split()[-1]
    # if name == "display":
    #     raise config.error(
    #         "0019: Section name [display display] is not valid. "
    #         "Please choose a different postfix.")
    # return wizard.load_config_prefix(config)
