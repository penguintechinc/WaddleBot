#!/bin/bash
ansible-playbook entrypoint.yml -c local --tags "run"
matterbridge -conf /etc/matterbridge/matterbridge.toml