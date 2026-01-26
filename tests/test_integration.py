#!/usr/bin/env python3
"""
Integration test for Claude Code session handling
"""
import subprocess
import json

def call_claude(prompt: str, session_id: str = None, continue_last: bool = False) -> tuple[str, str]:
    """
    Call Claude Code and return (response, session_id).
    This is the actual function from bot.py.
    """
    cmd = ["claude", "-p", prompt, "--output-format", "json"]

    if continue_last:
        cmd.append("--continue")
    elif session_id:
        cmd.extend(["--resume", session_id])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/home/dev"
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return data.get("result", result.stdout), data.get("session_id", session_id)
            except json.JSONDecodeError:
                return result.stdout, session_id
        else:
            return f"Error: {result.stderr}", session_id

    except subprocess.TimeoutExpired:
        return "Task timed out.", session_id
    except Exception as e:
        return f"Error calling Claude: {e}", session_id


def test_session_flow():
    """Test the complete session flow"""
    print("=" * 60)
    print("Test 1: New session (no flags)")
    print("=" * 60)
    response1, session1 = call_claude("Say 'test one'")
    print(f"Response: {response1[:100]}...")
    print(f"Session ID: {session1}")
    assert session1 is not None, "Session ID should be returned"
    print("✅ PASS\n")

    print("=" * 60)
    print("Test 2: Continue session")
    print("=" * 60)
    response2, session2 = call_claude("What did you just say?", continue_last=True)
    print(f"Response: {response2[:100]}...")
    print(f"Session ID: {session2}")
    assert session2 is not None, "Session ID should be returned"
    assert "test one" in response2.lower(), "Should remember previous message"
    print("✅ PASS\n")

    print("=" * 60)
    print("Test 3: Resume specific session")
    print("=" * 60)
    response3, session3 = call_claude("What was the very first thing I asked you?", session_id=session1)
    print(f"Response: {response3[:100]}...")
    print(f"Session ID: {session3}")
    assert session3 == session1, "Should return same session ID"
    print("✅ PASS\n")

    print("=" * 60)
    print("Test 4: Simulate bot.py flow")
    print("=" * 60)

    # Simulate user state
    user_state = {"current_session": None, "sessions": []}

    # First message
    continue_last = user_state["current_session"] is not None
    response, new_session_id = call_claude(
        "Hello bot",
        session_id=user_state["current_session"],
        continue_last=continue_last
    )
    print(f"First message - Session: {new_session_id[:8]}...")
    if new_session_id and new_session_id != user_state["current_session"]:
        user_state["current_session"] = new_session_id
        user_state["sessions"].append(new_session_id)

    # Second message (should continue)
    continue_last = user_state["current_session"] is not None
    response, new_session_id = call_claude(
        "What did I just say?",
        session_id=user_state["current_session"],
        continue_last=continue_last
    )
    print(f"Second message - Session: {new_session_id[:8]}...")
    assert "hello bot" in response.lower(), "Should remember first message"
    print("✅ PASS\n")

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_session_flow()
