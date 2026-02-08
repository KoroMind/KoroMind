"""Agent-evaluated tests for Brain output quality.

These tests give Brain real tasks and use an agent to evaluate
whether the output meets quality criteria. Non-deterministic but meaningful.

Run with: pytest -m eval -v
"""

import os
import re
from dataclasses import dataclass

import pytest
from dotenv import load_dotenv

from koro.core.brain import Brain

# Load environment variables
load_dotenv()


def _has_claude_auth():
    """Check for Claude authentication."""
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    from pathlib import Path

    creds_path = Path.home() / ".claude" / ".credentials.json"
    return creds_path.exists()


# Skip if no Claude auth
pytestmark = [
    pytest.mark.skipif(
        not _has_claude_auth(), reason="No Claude authentication configured"
    ),
    pytest.mark.eval,
    pytest.mark.live,
]


@dataclass
class EvalResult:
    """Result of agent evaluation."""

    passed: bool
    score: float  # 0.0 to 1.0
    reasoning: str
    criteria_met: dict[str, bool]


async def evaluate_response(
    brain: Brain,
    task_description: str,
    response_text: str,
    criteria: list[str],
) -> EvalResult:
    """
    Use the agent to evaluate if response meets criteria.

    Args:
        brain: Brain instance to use for evaluation
        task_description: What the original task was
        response_text: The response to evaluate
        criteria: List of criteria to check

    Returns:
        EvalResult with pass/fail, score, and reasoning
    """
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    eval_prompt = f"""You are an evaluator. Assess if this response meets the criteria.

ORIGINAL TASK: {task_description}

RESPONSE TO EVALUATE:
{response_text}

CRITERIA TO CHECK:
{criteria_text}

For each criterion, respond with PASS or FAIL.
Then give an overall score from 0.0 to 1.0.
Format your response EXACTLY like this:

CRITERION 1: PASS or FAIL
CRITERION 2: PASS or FAIL
...
SCORE: X.X
REASONING: Brief explanation
"""

    eval_response = await brain.process_text(
        user_id="evaluator",
        text=eval_prompt,
        include_audio=False,
    )

    # Parse evaluation response
    eval_text = eval_response.text
    criteria_met = {}

    for i, criterion in enumerate(criteria, 1):
        pattern = rf"CRITERION\s*{i}\s*:\s*(PASS|FAIL)"
        match = re.search(pattern, eval_text, re.IGNORECASE)
        if match:
            criteria_met[criterion] = match.group(1).upper() == "PASS"
        else:
            # Try alternate patterns
            if "pass" in eval_text.lower() and criterion.lower() in eval_text.lower():
                criteria_met[criterion] = True
            else:
                criteria_met[criterion] = False

    # Extract score
    score_match = re.search(r"SCORE\s*:\s*(\d+\.?\d*)", eval_text)
    score = float(score_match.group(1)) if score_match else 0.5

    # Extract reasoning
    reasoning_match = re.search(r"REASONING\s*:\s*(.+)", eval_text, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else eval_text[:200]

    # Calculate pass/fail
    passed = score >= 0.7 and sum(criteria_met.values()) >= len(criteria) * 0.7

    return EvalResult(
        passed=passed,
        score=score,
        reasoning=reasoning,
        criteria_met=criteria_met,
    )


@pytest.fixture
def brain(tmp_path):
    """Create Brain for evaluation tests."""
    from koro.core.claude import ClaudeClient
    from koro.core.state import StateManager

    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    state_manager = StateManager(db_path=str(tmp_path / "test.db"))
    claude_client = ClaudeClient(sandbox_dir=str(sandbox), working_dir=str(tmp_path))

    return Brain(
        state_manager=state_manager,
        claude_client=claude_client,
    )


class TestBrainCodeGeneration:
    """Evaluate Brain's code generation quality."""

    @pytest.mark.asyncio
    async def test_generates_working_python_function(self, brain):
        """Brain generates valid Python code."""
        task = "Write a Python function called 'add_numbers' that takes two numbers and returns their sum. Show me the code in your response."

        response = await brain.process_text(
            user_id="test_user",
            text=task,
            include_audio=False,
        )

        evaluation = await evaluate_response(
            brain=brain,
            task_description=task,
            response_text=response.text,
            criteria=[
                "Contains a Python function definition",
                "Function is named 'add_numbers' or similar",
                "Function takes two parameters",
                "Function returns the sum of the parameters",
            ],
        )

        assert (
            evaluation.passed
        ), f"Score: {evaluation.score}, Reasoning: {evaluation.reasoning}"

    @pytest.mark.asyncio
    async def test_generates_function_with_edge_cases(self, brain):
        """Brain handles edge cases in code generation."""
        task = "Write a Python function that calculates factorial. Handle edge cases like 0 and negative numbers. Show the code directly in your response, do not write it to a file."

        response = await brain.process_text(
            user_id="test_user",
            text=task,
            include_audio=False,
        )

        evaluation = await evaluate_response(
            brain=brain,
            task_description=task,
            response_text=response.text,
            criteria=[
                "Contains a factorial function",
                "Handles factorial of 0 (should return 1)",
                "Handles or validates negative numbers",
                "Uses recursion or iteration correctly",
            ],
        )

        assert (
            evaluation.passed
        ), f"Score: {evaluation.score}, Reasoning: {evaluation.reasoning}"


class TestBrainExplanation:
    """Evaluate Brain's explanation quality."""

    @pytest.mark.asyncio
    async def test_explains_concept_clearly(self, brain):
        """Brain explains concepts in understandable way."""
        task = "Explain what a hash table is and why it's useful, in simple terms."

        response = await brain.process_text(
            user_id="test_user",
            text=task,
            include_audio=False,
        )

        evaluation = await evaluate_response(
            brain=brain,
            task_description=task,
            response_text=response.text,
            criteria=[
                "Explains what a hash table is",
                "Mentions key-value pairs or lookup",
                "Explains why it's fast or useful",
                "Uses simple language appropriate for beginners",
            ],
        )

        assert (
            evaluation.passed
        ), f"Score: {evaluation.score}, Reasoning: {evaluation.reasoning}"


class TestBrainFileOperations:
    """Evaluate Brain's file operation tasks."""

    @pytest.mark.asyncio
    async def test_reads_and_summarizes_file(self, brain, tmp_path):
        """Brain reads file and provides accurate summary."""
        # Create test file
        test_file = tmp_path / "article.txt"
        test_file.write_text("""
        The Python programming language was created by Guido van Rossum.
        It was first released in 1991. Python emphasizes code readability
        and uses significant indentation. It supports multiple programming
        paradigms including procedural, object-oriented, and functional.
        Python is widely used for web development, data science, and automation.
        """)

        task = f"Read the file at {test_file} and give me a brief summary of what it's about."

        response = await brain.process_text(
            user_id="test_user",
            text=task,
            include_audio=False,
        )

        evaluation = await evaluate_response(
            brain=brain,
            task_description=task,
            response_text=response.text,
            criteria=[
                "Mentions Python programming language",
                "Mentions the creator (Guido van Rossum) or when it was created",
                "Mentions at least one key feature or use case",
                "Summary is concise (not just repeating the whole file)",
            ],
        )

        assert (
            evaluation.passed
        ), f"Score: {evaluation.score}, Reasoning: {evaluation.reasoning}"


class TestBrainMultiStep:
    """Evaluate Brain's multi-step task handling."""

    @pytest.mark.asyncio
    async def test_follows_multi_step_instructions(self, brain, tmp_path):
        """Brain executes multi-step tasks correctly."""
        # Create test file
        data_file = tmp_path / "numbers.txt"
        data_file.write_text("10\n20\n30\n40\n50")

        task = f"""Do these steps:
        1. Read the file at {data_file}
        2. Calculate the sum of all numbers in it
        3. Tell me the sum and the average
        """

        response = await brain.process_text(
            user_id="test_user",
            text=task,
            include_audio=False,
        )

        evaluation = await evaluate_response(
            brain=brain,
            task_description=task,
            response_text=response.text,
            criteria=[
                "Read the file (mentions reading or shows the numbers)",
                "Calculated the sum correctly (150)",
                "Calculated the average correctly (30)",
                "Presented results clearly",
            ],
        )

        assert (
            evaluation.passed
        ), f"Score: {evaluation.score}, Reasoning: {evaluation.reasoning}"
