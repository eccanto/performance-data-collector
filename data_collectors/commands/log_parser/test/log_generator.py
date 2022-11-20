"""Log generator example."""

import itertools
import logging
import time
from random import randint, random


_STAGES = [
    'stage 1',
    'stage 2 - message 1',
    'stage 3 - message 2',
    'stage 4',
]


def main():
    """Generates a log file example."""
    logging.basicConfig(filename='example.log', format='%(asctime)s:%(levelname)s: %(message)s', level=logging.DEBUG)

    for iteration in itertools.count(1):
        logging.info('# starting iteration "%s"...', iteration)
        try:
            for stage in _STAGES:
                if randint(1, 20) == 2:  # nosec B311
                    logging.error('fail detected.')
                    break

                logging.info(stage)
                time.sleep(random() * 2)  # nosec B311
        finally:
            logging.info('iteration "%s" finished.', iteration)


if __name__ == '__main__':
    main()
