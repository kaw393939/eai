"""Tests for workflow state management."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ei_cli.workflow.state import (
    WorkflowArtifact,
    WorkflowState,
    WorkflowStateManager,
)


class TestWorkflowArtifact:
    """Tests for WorkflowArtifact dataclass."""

    def test_create_artifact(self):
        """Test creating workflow artifact."""
        artifact = WorkflowArtifact(
            step_name="test_step",
            file_path=Path("/tmp/test.txt"),
            size_bytes=100,
        )

        assert artifact.step_name == "test_step"
        assert artifact.file_path == Path("/tmp/test.txt")
        assert artifact.size_bytes == 100

    def test_artifact_with_created_at(self):
        """Test artifact with created_at timestamp."""
        from datetime import datetime
        now = datetime.now()
        artifact = WorkflowArtifact(
            step_name="test_step",
            file_path=Path("/tmp/test.txt"),
            size_bytes=100,
            created_at=now,
        )

        assert artifact.created_at == now


class TestWorkflowState:
    """Tests for WorkflowState dataclass."""

    def test_create_state(self):
        """Test creating workflow state."""
        from datetime import datetime
        started = datetime(2024, 1, 1, 0, 0)

        state = WorkflowState(
            workflow_name="test_workflow",
            started_at=started,
        )

        assert state.workflow_name == "test_workflow"
        assert state.started_at == started
        assert state.completed_steps == []
        assert state.artifacts == {}

    def test_state_with_data(self):
        """Test state with completed steps and artifacts."""
        from datetime import datetime

        artifact = WorkflowArtifact(
            step_name="step1",
            file_path=Path("/tmp/test.txt"),
            size_bytes=100,
        )

        started = datetime(2024, 1, 1, 0, 0)
        state = WorkflowState(
            workflow_name="test_workflow",
            started_at=started,
            completed_steps=["step1", "step2"],
            artifacts={"step1": artifact},
        )

        assert len(state.completed_steps) == 2
        assert "step1" in state.artifacts
        assert state.artifacts["step1"].size_bytes == 100


class TestWorkflowStateManager:
    """Tests for WorkflowStateManager class."""

    @pytest.fixture
    def temp_workflow_dir(self, tmp_path):
        """Create temporary workflow directory."""
        return tmp_path

    @pytest.fixture
    def manager(self, temp_workflow_dir):
        """Create workflow state manager."""
        return WorkflowStateManager(
            workflow_name="test_workflow",
            workflow_dir=temp_workflow_dir,
        )

    def test_init_new_workflow(self, manager):
        """Test initializing new workflow."""
        assert manager.workflow_name == "test_workflow"
        assert manager.state.completed_steps == []
        assert manager.state.artifacts == {}

    def test_save_and_load_state(self, manager, temp_workflow_dir):
        """Test saving and loading workflow state."""
        # Mark a step as complete
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file)
        manager.save()

        # Create new manager and load state
        new_manager = WorkflowStateManager(
            workflow_name="test_workflow",
            workflow_dir=temp_workflow_dir,
        )

        assert new_manager.is_complete("step1")
        assert "step1" in new_manager.state.artifacts

    def test_mark_complete_with_checksum(self, manager, temp_workflow_dir):
        """Test marking step complete with checksum."""
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file, calculate_checksum=True)

        assert manager.is_complete("step1")
        artifact = manager.state.artifacts.get("step1")
        assert artifact is not None
        assert artifact.checksum is not None

    def test_mark_complete_without_checksum(self, manager, temp_workflow_dir):
        """Test marking step complete without checksum."""
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file, calculate_checksum=False)

        assert manager.is_complete("step1")
        artifact = manager.state.artifacts.get("step1")
        assert artifact is not None
        assert artifact.checksum is None

    def test_is_complete_false(self, manager):
        """Test checking incomplete step."""
        assert manager.is_complete("nonexistent_step") is False

    def test_get_artifact_none(self, manager):
        """Test getting artifact for nonexistent step."""
        artifact = manager.get_artifact("nonexistent_step")
        assert artifact is None

    def test_get_artifact_validates_existence(self, manager, temp_workflow_dir):
        """Test artifact validation checks file existence."""
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file)

        # Delete the file
        test_file.unlink()

        # Artifact should be invalid
        artifact = manager.get_artifact("step1")
        assert artifact is None

    def test_clear_state(self, manager, temp_workflow_dir):
        """Test clearing workflow state."""
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file)
        manager.save()

        state_file = manager.state_file
        assert state_file.exists()

        manager.reset()

        assert state_file.exists()  # reset() saves the state, doesn't delete it
        assert manager.state.completed_steps == []
        assert manager.state.artifacts == {}

    @patch("ei_cli.workflow.state.Confirm.ask")
    def test_should_resume_yes(self, mock_confirm, manager, temp_workflow_dir):
        """Test should_resume returns True when user confirms."""
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file)
        mock_confirm.return_value = True

        assert manager.should_resume() is True

    @patch("ei_cli.workflow.state.Confirm.ask")
    def test_should_resume_no(self, mock_confirm, manager, temp_workflow_dir):
        """Test should_resume returns False when user declines."""
        test_file = temp_workflow_dir / "test.txt"
        test_file.write_text("test content")

        manager.mark_complete("step1", test_file)
        mock_confirm.return_value = False

        # Should just return False, doesn't clear state automatically
        assert manager.should_resume() is False
        assert len(manager.state.completed_steps) == 1  # State remains

    def test_should_resume_no_state(self, manager):
        """Test should_resume returns False when no state exists."""
        assert manager.should_resume() is False

    def test_get_stats(self, manager, temp_workflow_dir):
        """Test getting workflow statistics."""
        test_file1 = temp_workflow_dir / "test1.txt"
        test_file1.write_text("test content 1")

        test_file2 = temp_workflow_dir / "test2.txt"
        test_file2.write_text("test content 2")

        manager.mark_complete("step1", test_file1)
        manager.mark_complete("step2", test_file2)

        stats = manager.get_stats()

        assert stats["workflow_name"] == "test_workflow"
        assert stats["steps_completed"] == 2  # Correct key name
        assert stats["artifacts_count"] == 2
        assert "total_size_mb" in stats  # Correct key name

    def test_state_file_path(self, manager, temp_workflow_dir):
        """Test state file is in correct location."""
        state_file = manager.state_file  # Use public attribute
        expected = temp_workflow_dir / ".workflow_state.json"

        assert state_file == expected

    def test_save_creates_directory(self, tmp_path):
        """Test save creates workflow directory if needed."""
        workflow_dir = tmp_path / "nonexistent"

        manager = WorkflowStateManager(
            workflow_name="test",
            workflow_dir=workflow_dir,
        )

        manager.save()

        assert workflow_dir.exists()
        assert (workflow_dir / ".workflow_state.json").exists()

    def test_load_invalid_json(self, manager, temp_workflow_dir):
        """Test loading invalid JSON creates new state."""
        state_file = temp_workflow_dir / ".workflow_state.json"
        state_file.write_text("invalid json{")

        # Should create new state without error
        new_manager = WorkflowStateManager(
            workflow_name="test_workflow",
            workflow_dir=temp_workflow_dir,
        )

        assert len(new_manager.state.completed_steps) == 0
