import logging
import logging.config

from scruffy import Environment
from .main import main

env = None
config = None

def setup_env():
    global env, config
    env = Environment({
        'dir':  {
            'path': '~/.windfarm',
            'create': True,
            'mode': 448 # 0700
        },
        'files': {
            'config': {
                'type':     'config',
                'default':  {
                    'path':     'config/default.cfg',
                    'rel_to':   'pkg',
                    'pkg':      'windfarm'
                },
                'read':     True
            },
            'state': {
                'type':     'raw',
                'read':     False
            }
        },
        'basename': 'windfarm'
    })
    config = env['config']

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'standard': {'format': '%(levelname)s: %(message)s'}
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard'
            }
        },
        'loggers': {
            'bot': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False
            }
        }
    })


setup_env()