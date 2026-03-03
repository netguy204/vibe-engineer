# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated tests for ClaudeSDKClient migration
"""Tests for the orchestrator agent runner - SPLIT FILE.

This file has been split into focused modules for better maintainability.
Tests have been moved to the following files:

- test_orchestrator_agent_skills.py - Skill files, content loading, error detection, AgentRunner basics
- test_orchestrator_agent_runner.py - Phase execution, settings, log callbacks, question hooks
- test_orchestrator_agent_callbacks.py - Question callbacks, sandbox violation detection, hook merging
- test_orchestrator_agent_sandbox.py - Sandbox enforcement hooks and integration
- test_orchestrator_agent_review.py - Review decision hooks, callbacks, MCP server config
- test_orchestrator_agent_stream.py - AskUserQuestion message stream capture

This file is kept as a reference and to ensure backward compatibility with
any test collection that explicitly imports from this module.
"""

# Re-export common test infrastructure for backward compatibility
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from orchestrator.agent import PHASE_SKILL_FILES


class MockClaudeSDKClient:
    """Mock for ClaudeSDKClient that supports async context manager pattern.

    This mock simulates the ClaudeSDKClient behavior:
    - Async context manager (__aenter__/__aexit__)
    - query() method to send prompts
    - receive_response() async iterator for messages

    This class is re-exported for backward compatibility. The actual
    test infrastructure is now in the split files.
    """
    last_instance = None
    all_instances = []

    def __init__(self, options=None):
        self.options = options
        self._messages = []
        self._exception = None
        self._query_prompt = None
        MockClaudeSDKClient.last_instance = self
        MockClaudeSDKClient.all_instances.append(self)

    @classmethod
    def reset(cls):
        cls.last_instance = None
        cls.all_instances = []

    def set_messages(self, messages):
        self._messages = messages

    def set_exception(self, exc):
        self._exception = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def query(self, prompt):
        self._query_prompt = prompt

    async def receive_response(self):
        if self._exception:
            raise self._exception
        for msg in self._messages:
            yield msg


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory with skill files for testing.

    This fixture is re-exported for backward compatibility.
    """
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    skill_content = """---
description: Test skill
---

## Instructions

This is a test skill for {phase}.
"""
    for phase, filename in PHASE_SKILL_FILES.items():
        (commands_dir / filename).write_text(
            skill_content.format(phase=phase.value)
        )

    return tmp_path
