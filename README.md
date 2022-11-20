[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)

# Performance and logfile data collector with Python, Kibana and Elasticsearch

# Table of contents

* [Overview](#overview)
* [Get started](#get-started)
  * [Requirements](#requirements)
  * [Deploy Dashboard](#deploy-dashboard)
    * [Requirements](#requirements)
  * [Run Collectors](#run-collectors)
    * [Requirements](#requirements-1)
    * [Run performance data collector](#run-performance-data-collector)
    * [Run log file data collector](#run-log-file-data-collector)
* [Static code analysis tools](#static-code-analysis-tools)
  * [Set up the Git hooks custom directory](#set-up-the-git-hooks-custom-directory)
  * [Python Static Checkers](#python-static-checkers)
  * [Shell Static Checkers](#shell-static-checkers)
* [License](#license)

# Overview

Project to collect useful data from processes, system and log files for post analysis using graphical tools.

# Get Started

## Deploy Dashboard

### Requirements

- [Docker +20.10.21](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose plugin +v2.12.2](https://docs.docker.com/compose/install/linux/)

Deploy Kibana and Elasticsearch services.

```bash
cd dashboard/
docker compose up
```

Default account:
  - username: `admin`
  - password: `admin`

Web:
- Kibana dashboard: http://localhost:5601/
- Elasticsearch indices: http://localhost:9200/_cat/indices

![Dashboard](documentation/images/dashboard.gif)

## Run Collectors

### Requirements

```bash
cd data_collectors/
python3 -m pip install -r requirements.txt
```

### Run performance data collector

```bash
cd data_collectors/
python3 main.py --elasticsearch_index "performance-data" --elasticsearch_url "http://admin:admin@localhost:9200" processes_data --interval "0.25" --process "htop"
```

### Run log file data collector

`Terminal 1`: run test log generator:

```bash
cd data_collectors/
python3 commands/log_parser/test/log_generator.py
```

`Terminal 2`: run collector:

```bash
cd data_collectors/
python3 main.py --elasticsearch_index "log-data" --elasticsearch_url "http://admin:admin@localhost:9200" log_parser --log_file "example.log" --stage_file "commands/log_parser/test/stages.yml"
```

# Static code analysis tools

These are the linters that will help us to follow good practices and style guides of our source code. We will be using the following static analysis tools, which will be executed when generating a new push in the repository (git hooks).

## Set up the Git hooks custom directory

After cloning the repository run the following command in the repository root:

```bash
git config core.hooksPath .githooks
```

## Python Static Checkers

Tools used:
- [brunette](https://github.com/odwyersoftware/brunette): A best practice Python code formatter.
- [isort](https://pycqa.github.io/isort/): Python utility / library to sort imports alphabetically, and automatically separated into sections and by type.
- [prospector](https://github.com/PyCQA/prospector): Prospector is a tool to analyse Python code and output information about errors, potential problems, convention violations and complexity.

  Tools executed by Prospector:
  - [pylint](https://github.com/PyCQA/pylint): Pylint is a Python static code analysis tool which looks for programming errors,   helps enforcing a coding standard, sniffs for code smells and offers simple refactoring suggestions.
  - [bandit](https://github.com/PyCQA/bandit): Bandit is a tool designed to find common security issues.
  - [dodgy](https://github.com/landscapeio/dodgy): It is a series of simple regular expressions designed to detect things such as accidental SCM diff checkins, or passwords or secret keys hard coded into files.
  - [mccabe](https://github.com/PyCQA/mccabe): Complexity checker.
  - [mypy](https://github.com/python/mypy): Mypy is an optional static type checker for Python.
  - [pydocstyle](https://github.com/PyCQA/pydocstyle): pydocstyle is a static analysis tool for checking compliance with Python [PEP 257](https://peps.python.org/pep-0257/).
  - [pycodestyle](https://pycodestyle.pycqa.org/en/latest/): pycodestyle is a tool to check your Python code against some of the style conventions in [PEP 8](https://peps.python.org/pep-0008/).
  - [pyflakes](https://github.com/PyCQA/pyflakes): Pyflakes analyzes programs and detects various errors.
  - [pyroma](https://github.com/regebro/pyroma): Pyroma is a product aimed at giving a rating of how well a Python project complies with the best practices of the Python packaging ecosystem, primarily PyPI, pip, Distribute etc, as well as a list of issues that could be improved.

## Shell Static Checkers

Tools used:
- [shellcheck](https://www.shellcheck.net/): Finds bugs in your shell scripts (bash).

  Installation:

  ```bash
  apt install shellcheck
  ```

## Run manually

```bash
cd data_collectors
bash scripts/code_checkers.sh
cd -
```

# License

[MIT](./LICENSE)
