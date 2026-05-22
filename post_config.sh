#!/bin/bash
# Auto-generated post_config script

echo "Running: gitignore"
cat *.gitignore > .gitignore && rm *.gitignore
echo "Running: Initialize git repository"
git init
echo "Running: Install git-lfs hooks"
git lfs install
