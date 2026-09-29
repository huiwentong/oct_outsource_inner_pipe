name = 'oct_outsource_inner_pipe'

version = '0.0.1'


requires = [
    'psycopg2',
    'PySide6',
    'PyYAML',
    'requests',
    'shotgun_api3'
]


def commands():
    env.PYTHONPATH.append('{root}/gui_manager')
    alias('run_collector', 'python {root}/gui_manager/collector.py')
    alias('run_usermanager', 'python {root}/gui_manager/usermanager.py')
