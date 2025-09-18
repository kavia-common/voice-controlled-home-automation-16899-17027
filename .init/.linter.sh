#!/bin/bash
cd /home/kavia/workspace/code-generation/voice-controlled-home-automation-16899-17027/VoiceProcessingBackend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

