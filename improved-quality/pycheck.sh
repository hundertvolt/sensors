#!/bin/bash
ruff format --line-length 120 $1
mypy $1
ruff check --line-length 120 --ignore E722 $1
