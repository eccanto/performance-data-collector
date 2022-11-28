"""Collect performance data by process names."""

import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import click
import coloredlogs
import yaml


class LogLine:
    """Log line parser."""

    _DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

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
    while not path.exists():
        logging.info('waiting log file: %s...', path)
        time.sleep(1)

    with open(path, encoding='UTF-8') as file_object:
        while True:
            line = file_object.readline().strip()
            if not line:
                time.sleep(0.1)
                continue

            yield line


def _process_block(block, stages_data, delta_time):
    data = defaultdict(lambda: defaultdict(lambda: {}))
    data['duration'] = (block[-1].date - block[0].date).total_seconds()

    data['@timestamp'] = block[0].date.astimezone() + timedelta(hours=delta_time)
    data['@real_timestamp'] = block[0].date.astimezone()

    begin_position, end_position = 0, len(block)
    for stage in stages_data['stages']:
        stage_block = []
        begin_stage = end_stage = None
        for index in range(begin_position, end_position):
            sub_line = block[index]
            if re.match(stage['begin'], sub_line.line):
                begin_stage = sub_line
                stage_block = [sub_line.line]
            elif stage_block and re.match(stage['end'], sub_line.line):
                end_stage = sub_line
                stage_block.append(sub_line.line)
                begin_position = index
                break
            elif stage_block:
                stage_block.append(sub_line.line)

        if (begin_stage is None) or (end_stage is None):
            logging.warning('Stage not found: "%s" -> "%s"', stage['begin'], stage['end'])

        data['stage'][stage['id']]['lines'] = stage_block
        data['stage'][stage['id']]['duration'] = (end_stage.date - begin_stage.date).total_seconds()

    return data


@click.command('Collect log file data by messages.')
@click.option('-l', '--log_file', help='Log file path', type=click.Path(path_type=Path), required=True)
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
    delta_time = context.obj['delta_time']

    logging.info('parsing log file: %s... (press Ctrl+C to stop)', log_file)

    with open(stage_file, encoding='UTF-8') as yaml_file:
        stages_data = yaml.safe_load(yaml_file)

    block, ignored_lines = None, []
    for line in follow_file(log_file):
        try:
            log_line = LogLine(line, stages_data['date_pattern'])
            if re.match(stages_data['first'], log_line.line):
                block = [log_line]
            elif block and re.match(stages_data['end'], log_line.line):
                block.append(log_line)
                block.sort()

                elasticsearch_client.index(
                    index=elasticsearch_index, document=_process_block(block, stages_data, delta_time)
                )
            elif block:
                block.append(log_line)
        except AttributeError:
            if line not in ignored_lines:
                logging.warning('ignoring line: "%s"...', line)
                ignored_lines.append(line)
