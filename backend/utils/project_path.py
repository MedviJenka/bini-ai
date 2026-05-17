import os

# Full project path which used to strip to get a global path
abstract_dir = os.path.dirname(os.path.abspath(__file__))

# Automation
GLOBAL_PATH = abstract_dir.split('backend')[0][:-1]
TESTS = fr'{GLOBAL_PATH}\tests'
BINI_LOGS = fr'{GLOBAL_PATH}\tests\logs\logs.log'
BINI_RESULTS = fr'{GLOBAL_PATH}\results'
LOGS = fr'{GLOBAL_PATH}/logs'
HTML_FILE = fr'{GLOBAL_PATH}\tests\data\tenants.html'
