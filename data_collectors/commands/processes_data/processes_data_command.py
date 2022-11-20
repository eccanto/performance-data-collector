"""Collect performance data by process names."""

import itertools
import json
import logging
import subprocess  # nosec B404
import time
from collections import defaultdict
from datetime import datetime
from pydoc import locate

import click
import coloredlogs
import psutil
from elasticsearch.helpers import bulk


_DEFAULT_INTERVAL = 0.25
_SAMPLE_SIZE = 20


def _get_psutil_processes(process_names):
    processes_objects = []
    for process_name in process_names:
        while not (
            process := next((process for process in psutil.process_iter() if process.name() == process_name), None)
        ):
            logging.info('waiting process: %s...', process_name)
            time.sleep(1)

        processes_objects.append(process)
    return processes_objects


def _run_command(command):
    # pylint: disable=subprocess-run-check
    return subprocess.run(command, stdout=subprocess.PIPE, shell=True).stdout.decode().strip()  # nosec B602


def _get_system_data():
    system_data = defaultdict(lambda: defaultdict(lambda: {}))

    memory_info = psutil.virtual_memory()
    system_data['memory']['total'] = memory_info.total
    system_data['memory']['available'] = memory_info.available
    system_data['memory']['percent'] = memory_info.percent
    system_data['memory']['used'] = memory_info.used
    system_data['memory']['free'] = memory_info.free
    system_data['memory']['active'] = memory_info.active
    system_data['memory']['inactive'] = memory_info.inactive
    system_data['memory']['buffers'] = memory_info.buffers
    system_data['memory']['cached'] = memory_info.cached
    system_data['memory']['shared'] = memory_info.shared
    system_data['memory']['slab'] = memory_info.slab

    cpu_times = psutil.cpu_times()
    system_data['cpu']['percent'] = psutil.cpu_percent()
    system_data['cpu']['user'] = cpu_times.user
    system_data['cpu']['system'] = cpu_times.system
    system_data['cpu']['idle'] = cpu_times.idle
    system_data['cpu']['iowait'] = cpu_times.iowait
    system_data['cpu']['irq'] = cpu_times.irq
    system_data['cpu']['softirq'] = cpu_times.softirq

    io_counters = psutil.disk_io_counters()
    system_data['io']['read_count'] = io_counters.read_count
    system_data['io']['write_count'] = io_counters.write_count
    system_data['io']['read_bytes'] = io_counters.read_bytes
    system_data['io']['write_bytes'] = io_counters.write_bytes
    system_data['io']['read_time'] = io_counters.read_time
    system_data['io']['write_time'] = io_counters.write_time
    system_data['io']['busy_time'] = io_counters.busy_time

    return system_data


def _get_processes_data(processses):
    processses_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {})))
    for process in processses:
        memory_info = process.memory_full_info()
        processses_data[process.name()]['memory']['rss'] = memory_info.rss
        processses_data[process.name()]['memory']['vms'] = memory_info.vms
        processses_data[process.name()]['memory']['shared'] = memory_info.shared

        cpu_times = process.cpu_times()
        processses_data[process.name()]['cpu']['user_time'] = cpu_times.user
        processses_data[process.name()]['cpu']['system_time'] = cpu_times.system
        processses_data[process.name()]['cpu']['cpu_percent'] = process.cpu_percent()

        io_counters = process.io_counters()
        processses_data[process.name()]['io']['read_count'] = io_counters.read_count
        processses_data[process.name()]['io']['write_count'] = io_counters.write_count
        processses_data[process.name()]['io']['read_bytes'] = io_counters.read_bytes
        processses_data[process.name()]['io']['write_bytes'] = io_counters.write_bytes

    return processses_data


@click.command('Collect machine performance data.')
@click.option(
    '-i',
    '--interval',
    help=f'Interval in seconds (default: {_DEFAULT_INTERVAL}).',
    type=float,
    default=_DEFAULT_INTERVAL,
    required=True,
)
@click.option(
    '-p',
    '--process',
    'processes',
    multiple=True,
    help=(
        'Process names. If you want to use multiple processes you should specify twice: '
        '--process process1 --process process2.'
    ),
)
@click.option(
    '-c',
    '--command',
    'commands',
    multiple=True,
    help=(
        'Custom commands (JSON format). If you want to use multiple commands you should specify twice: '
        '--command command1 --command command2.'
    ),
)
@click.pass_context
def processes_data_command(context, interval, processes, commands):
    """Collect performance data by process names.

    Command example:
        '{ "name": "xml_files", "command": "ls -l ~ | wc -l", "type": "int" }'

    :param contenxt: The Context object created by the click module which holds state for this particular invocation.
    """
    coloredlogs.install(
        fmt='%(asctime)s,%(msecs)03d %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s', level='INFO'
    )

    logging.info('getting data: %s... (press Ctrl+C to stop)', processes)

    elasticsearch_index = context.obj['elasticsearch_index']
    elasticsearch_client = context.obj['elasticsearch_client']

    commands = [json.loads(command) for command in commands]
    processes_objects = _get_psutil_processes(processes)

    data = []
    try:
        for iteration in itertools.count(1):
            iteration_data = defaultdict(lambda: defaultdict(lambda: {}))

            iteration_data['@timestamp'] = datetime.utcnow().isoformat()
            iteration_data['system'] = _get_system_data()
            iteration_data['processes'] = _get_processes_data(processes_objects)

            for command in commands:
                iteration_data['custom'][command['name']] = locate(command['type'])(_run_command(command['command']))

            data.append(iteration_data)

            if iteration % _SAMPLE_SIZE == 0:
                bulk(
                    elasticsearch_client, [{'_index': elasticsearch_index, '_source': item_data} for item_data in data]
                )
                data = []

            time.sleep(interval)
    except (KeyboardInterrupt, psutil.NoSuchProcess):
        logging.info('stopping collection...')

        if data:
            bulk(elasticsearch_client, [{'_index': elasticsearch_index, '_source': item_data} for item_data in data])