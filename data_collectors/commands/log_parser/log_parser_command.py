"""Collect performance data by process names."""

import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click
import coloredlogs
import yaml


class LogLine:
    """Log line parser."""

    _DATE_FORMAT = '%Y-%m-%d %H:%M:%S,%f'

    def __init__(self, line, date_format):
        """Constructor method."""
        self.line = line.strip()

        self.date_string = re.match(date_format, line).group(1)
        self.date = datetime.strptime(self.date_string, self._DATE_FORMAT)

    def __repr__(self):
        """Object instance representation."""
        return self.line

    def __lt__(self, other):
        """Less than comparison."""
        return self.date < other.date


def follow_file(path):
    """Generator function that yields new lines in a file."""
    with open(path, encoding='UTF-8') as file_object:
        while True:
            line = file_object.readline()
            if not line:
                time.sleep(0.1)
                continue

            yield line


@click.command('Collect log file data by messages.')
@click.option('-l', '--log_file', help='Log file path', type=click.Path(exists=True, path_type=Path), required=True)
@click.option('-s', '--stage_file', help='Stage file path', type=click.Path(exists=True, path_type=Path), required=True)
@click.pass_context
def log_parser_command(context, log_file, stage_file):
    """Collect log file data by messages.

    :param contenxt: The Context object created by the click module which holds state for this particular invocation.
    """
    coloredlogs.install(
        fmt='%(asctime)s,%(msecs)03d %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s', level='INFO'
    )

    elasticsearch_index = context.obj['elasticsearch_index']
    elasticsearch_client = context.obj['elasticsearch_client']

    logging.info('parsing log file: %s... (press Ctrl+C to stop)', log_file)

    with open(stage_file, encoding='UTF-8') as yaml_file:
        stages_data = yaml.safe_load(yaml_file)

    block = []
    for log_line in (LogLine(line, stages_data['date_pattern']) for line in follow_file(log_file)):
        if re.match(stages_data['first'], log_line.line):
            block = [log_line]
        elif re.match(stages_data['end'], log_line.line):
            block.append(log_line)
            block.sort()

            data = defaultdict(lambda: defaultdict(lambda: {}))
            data['duration'] = (block[-1].date - block[0].date).total_seconds()
            data['@timestamp'] = block[0].date.astimezone()

            start_time = block[0].date
            for log_line in block[1:]:
                for stage in stages_data['stages']:
                    if re.match(stage['pattern'], log_line.line):
                        data['stage'][stage['id']]['line'] = log_line.line
                        data['stage'][stage['id']]['duration'] = (log_line.date - start_time).total_seconds()
                        start_time = log_line.date
                        break

            elasticsearch_client.index(index=elasticsearch_index, document=data)
        else:
            block.append(log_line)
