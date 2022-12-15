"""Collect performance data by process names."""

import logging
import re
import time
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from pydoc import locate

import click
import coloredlogs
import yaml
from dateutil.parser import parse


class LogLine:
    """Log line parser."""

    _DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

    def __init__(self, line, date_format):
        """Constructor method."""
        self.line = line.strip()

        self.date_string = re.match(date_format, line).group(1)
        self.date = parse(self.date_string)

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


def _process_value(value_id, value_data, log_line, delta_time):
    data = defaultdict(lambda: defaultdict(lambda: {}))

    data['@timestamp'] = log_line.date.astimezone() + timedelta(hours=delta_time)
    data['@real_timestamp'] = log_line.date.astimezone()

    data['value'][value_id]['line'] = log_line.line
    data['value'][value_id]['value'] = value_data

    return data


def _process_block(block, stages_data, delta_time):
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {})))
    data['duration'] = (block[-1].date - block[0].date).total_seconds()

    data['lines'] = [line.line for line in block]

    data['@timestamp'] = block[0].date.astimezone() + timedelta(hours=delta_time)
    data['@real_timestamp'] = block[0].date.astimezone()

    for stage in stages_data['stages']:
        stage_block = []
        for line in block:
            if not stage_block and re.match(stage['begin'], line.line):
                stage_block = [line]
                if stage['begin'] == stage['end']:
                    break
            elif stage_block and re.match(stage['end'], line.line):
                stage_block.append(line)
                break
            elif stage_block:
                stage_block.append(line)
        else:
            logging.warning('Stage not found: "%s" (from "%s" to "%s")', stage['id'], block[0].date, block[-1].date)
            continue

        data['stage'][stage['id']]['lines'] = [line.line for line in stage_block]
        data['stage'][stage['id']]['duration'] = (stage_block[-1].date - stage_block[0].date).total_seconds()

    for value in stages_data['values']:
        for line in block:
            match = re.match(value['pattern'], line.line)
            if match:
                try:
                    data['stage']['value'][value['id']]['line'] = line.line
                    data['stage']['value'][value['id']]['value'] = locate(value['type'])(match.group(1))
                    break
                except IndexError as error:
                    logging.warning('Invalid value pattern group (%s): %s', value['pattern'], error)
                except TypeError as error:
                    logging.warning('Invalid value type (%s): %s', value['type'], error)
                except ValueError as error:
                    logging.warning('Unexpected cast (%s): %s', value['type'], error)
        else:
            logging.warning('Value not found: "%s" (from "%s" to "%s")', value['id'], block[0].date, block[-1].date)

    return data


@click.command('Collect log file data by messages.')
@click.option('-l', '--log_file', help='Log file path', type=click.Path(path_type=Path), required=True)
@click.option('-s', '--stage_file', help='Stage file path', type=click.Path(exists=True, path_type=Path), required=True)
@click.pass_context
def log_parser_command(context, log_file, stage_file):
    """Collect log file data by messages.

    :param context: The Context object created by the click module which holds state for this particular invocation.
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
            if re.match(stages_data['block']['begin'], log_line.line):
                block = [log_line]
            elif block and re.match(stages_data['block']['end'], log_line.line):
                block.append(log_line)
                block.sort()

                elasticsearch_client.index(
                    index=elasticsearch_index, document=_process_block(block, stages_data['block'], delta_time)
                )
                block = []
            elif block:
                block.append(log_line)

            for value_pattern in stages_data['values']:
                match = re.match(value_pattern['pattern'], log_line.line)
                if match:
                    elasticsearch_client.index(
                        index=elasticsearch_index, document=_process_value(
                            value_pattern['id'], locate(value_pattern['type'])(match.group(1)), log_line, delta_time
                            )
                    )

        except AttributeError:
            if line not in ignored_lines:
                logging.warning('ignoring line: "%s"...', line)
                ignored_lines.append(line)
