#!/usr/bin/env python3

"""Entry point to Command Line Interface tool."""

import logging

import click
import coloredlogs
from elasticsearch import Elasticsearch

from commands.log_parser.log_parser_command import log_parser_command
from commands.processes_data.processes_data_command import processes_data_command


_DEFAULT_DELTA_TIME = 0


@click.group(help='Command Line Interface tool to manage automated test cycles of the project in Jira.')
@click.option('-x', '--elasticsearch_index', help='Elasticsearch index.', required=True)
@click.option('-e', '--elasticsearch_url', help='Elasticsearch URL.', required=True)
@click.option(
    '-d',
    '--delta_time',
    help='Delta time in hours (default: {_DEFAULT_DELTA_TIME}).',
    default=_DEFAULT_DELTA_TIME,
    type=int,
)
@click.pass_context
def main(context, elasticsearch_index, elasticsearch_url, delta_time):
    """Main command line interface function composed of subcommands, takes general arguments to pass to subcommands."""
    coloredlogs.install(fmt='%(asctime)s-%(name)s-%(levelname)s: %(message)s', level=logging.INFO)

    context.ensure_object(dict)

    elasticsearch_client = Elasticsearch(elasticsearch_url, verify_certs=False)

    context.obj['elasticsearch_index'] = elasticsearch_index
    context.obj['elasticsearch_client'] = elasticsearch_client
    context.obj['delta_time'] = delta_time


main.add_command(log_parser_command, name='log_parser')
main.add_command(processes_data_command, name='processes_data')


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
