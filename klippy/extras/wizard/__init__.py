import importlib


def load_config_prefix(config):
    mod_name = 'extras.wizard.' + config.get_name().split()[0]
    try:
        mod = importlib.import_module(mod_name)
        return mod.load_config_prefix(config)
    except Exception as e:
        raise Exception('2050: No module named %s, error: %s' % (mod_name, e))
