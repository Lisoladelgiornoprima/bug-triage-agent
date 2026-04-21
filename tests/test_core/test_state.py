"""Tests for WorkflowState."""

from src.core.state import WorkflowState, WorkflowStatus


def test_initial_state():
    """Test default state values."""
    state = WorkflowState()
    assert state.status == WorkflowStatus.PENDING
    assert state.current_phase == ""
    assert state.data == {}
    assert state.errors == []


def test_update_and_get():
    """Test storing and retrieving data."""
    state = WorkflowState()
    state.update("issue_analysis", {"title": "test bug"})

    result = state.get("issue_analysis")
    assert result == {"title": "test bug"}


def test_get_default():
    """Test get with default value."""
    state = WorkflowState()
    result = state.get("nonexistent", "default_value")
    assert result == "default_value"


def test_add_error():
    """Test error recording."""
    state = WorkflowState()
    state.add_error("phase1", "something went wrong")

    assert len(state.errors) == 1
    assert state.errors[0]["phase"] == "phase1"
    assert state.errors[0]["error"] == "something went wrong"


def test_save_and_load_checkpoint(tmp_path):
    """Test checkpoint save and load."""
    state = WorkflowState()
    state.status = WorkflowStatus.IN_PROGRESS
    state.current_phase = "code_location"
    state.update("issue_analysis", {"title": "test"})
    state.add_error("phase1", "warning")

    checkpoint_path = tmp_path / "checkpoint.json"
    state.save_checkpoint(checkpoint_path)

    loaded = WorkflowState.load_checkpoint(checkpoint_path)
    assert loaded.status == WorkflowStatus.IN_PROGRESS
    assert loaded.current_phase == "code_location"
    assert loaded.get("issue_analysis") == {"title": "test"}
    assert len(loaded.errors) == 1
