#!/bin/sh
# busy loop for $1 seconds
end=$(( $(date +%s) + $1 ))
while [ $(date +%s) -lt $end ]; do i=0; while [ $i -lt 20000 ]; do i=$((i+1)); done; done
