#!/bin/sh

set -eu

while IFS=' ' read -r local_ref local_sha remote_ref remote_sha
do
    if [ "${remote_ref}" = "refs/heads/main" ]; then
        printf '%s\n' "Direct pushes to 'main' are blocked. Open a pull request instead." >&2
        exit 1
    fi
done

exit 0
