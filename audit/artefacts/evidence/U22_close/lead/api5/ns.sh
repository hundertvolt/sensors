#!/bin/bash
# ns.sh <cmd...>: inside a fresh network namespace, bring loopback up and run the command.
ip link set lo up || exit 2
exec "$@"
