#!/bin/bash
export SKIP=no-commit-to-branch
mkdocs gh-deploy --clean
unset SKIP
