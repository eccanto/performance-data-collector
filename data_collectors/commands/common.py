"""Common code of the subcommands."""

import sys

import click
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Search


def _check_collection(elasticsearch_client, index, collection):
    query = Search(using=elasticsearch_client, index=index).filter('term', collection=collection)
    try:
        if query.execute() and not click.confirm(
            f'The collection "{collection}" already exists, do you want to continue?', default=False
        ):
            sys.exit(1)
    except NotFoundError:
        pass
