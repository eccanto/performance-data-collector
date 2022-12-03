"""Log generator example."""

import itertools
import logging
import time
from random import randint, random


_STAGES = [
    {
        'begin': 'stage 1',
        'end': 'end - stage 1',
    },
    {
        'begin': 'stage 2',
        'end': 'end - stage 2',
    },
    {
        'begin': 'stage 3',
        'end': 'end - stage 3',
    },
    {
        'begin': 'stage 4',
        'end': 'end - stage 4',
    },
]


def main():
    """Generates a log file example."""
    logging.basicConfig(filename='example.log', format='%(asctime)s:%(levelname)s: %(message)s', level=logging.DEBUG)

    for iteration in itertools.count(1):
        logging.info('# starting block %s', iteration)
        try:
            for stage in _STAGES:
                if randint(1, 20) == 2:  # nosec B311
                    logging.error('fail-1 detected')
                    break

                logging.info(stage['begin'])

                if randint(1, 20) == 2:  # nosec B311
                    logging.error('fail-2 detected')
                    break

                time.sleep(random() * 2)  # nosec B311

                logging.info(stage['end'])
        finally:
            logging.info('block finished')


if __name__ == '__main__':
    main()
