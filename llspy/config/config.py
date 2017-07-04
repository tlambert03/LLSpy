import os
from configparser import ConfigParser

configdir = os.path.dirname(os.path.abspath(__file__))
__CONFIGFILE__ = os.path.abspath(os.path.join(configdir, "settings.ini"))

user_settings = ConfigParser()
user_settings.read(__CONFIGFILE__)
