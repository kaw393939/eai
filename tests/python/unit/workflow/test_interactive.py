"""Tests for interactive workflow management."""

import os
from unittest.mock import patch

import pytest

from ei_cli.workflow.interactive import (
    InteractiveWorkflow,
    RecoveryAction,
    WorkflowMode,
    with_error_recovery,
)


class TestWorkflowMode:
    """Tests for WorkflowMode enum."""

    def test_modes_exist(self):
        """Test all workflow modes are defined."""
        assert WorkflowMode.INTERACTIVE.value == "interactive"
        assert WorkflowMode.AUTO.value == "auto"
        assert WorkflowMode.HEADLESS.value == "headless"


class TestRecoveryAction:
    """Tests for RecoveryAction enum."""

    def test_actions_exist(self):
        """Test all recovery actions are defined."""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.SKIP.value == "skip"
        assert RecoveryAction.ABORT.value == "abort"
        assert RecoveryAction.CONTINUE.value == "continue"


class TestInteractiveWorkflow:
    """Tests for InteractiveWorkflow class."""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("sys.stdout.isatty", return_value=True)
    def test_init_default(self, mock_stdout_isatty, mock_stdin_isatty):
        """Test default initialization."""
        with patch.dict(os.environ, {}, clear=True):
            workflow = InteractiveWorkflow()
            assert workflow.mode == WorkflowMode.INTERACTIVE

    def test_init_custom_mode(self):
        """Test custom mode initialization."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        assert workflow.mode == WorkflowMode.HEADLESS

    def test_detect_mode_ci(self):
        """Test CI environment detection."""
        with patch.dict(os.environ, {"CI": "true"}):
            workflow = InteractiveWorkflow()
            assert workflow.mode == WorkflowMode.HEADLESS

    def test_detect_mode_github_actions(self):
        """Test GitHub Actions detection."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            workflow = InteractiveWorkflow()
            assert workflow.mode == WorkflowMode.HEADLESS

    def test_is_interactive(self):
        """Test is_interactive check."""
        workflow_interactive = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        workflow_headless = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)

        assert workflow_interactive.is_interactive() is True
        assert workflow_headless.is_interactive() is False

    @patch("ei_cli.workflow.interactive.Confirm.ask")
    def test_confirm_step_interactive_yes(self, mock_confirm):
        """Test confirm_step in interactive mode with yes."""
        mock_confirm.return_value = True

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        result = workflow.confirm_step("Download video")

        assert result is True
        mock_confirm.assert_called_once()

    @patch("ei_cli.workflow.interactive.Confirm.ask")
    def test_confirm_step_interactive_no(self, mock_confirm):
        """Test confirm_step in interactive mode with no."""
        mock_confirm.return_value = False

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        result = workflow.confirm_step("Download video")

        assert result is False
        mock_confirm.assert_called_once()

    def test_confirm_step_headless_default_true(self):
        """Test confirm_step in headless mode with default=True."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        result = workflow.confirm_step("Download video", default=True)

        assert result is True

    def test_confirm_step_headless_default_false(self):
        """Test confirm_step in headless mode with default=False."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        result = workflow.confirm_step("Download video", default=False)

        assert result is False

    @patch("ei_cli.workflow.interactive.Confirm.ask")
    def test_confirm_step_expensive(self, mock_confirm):
        """Test confirm_step with expensive=True shows warning."""
        mock_confirm.return_value = True

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        result = workflow.confirm_step(
            "Process large file",
            expensive=True,
        )

        assert result is True

    @patch("ei_cli.workflow.interactive.Prompt.ask")
    def test_handle_error_interactive_retry(self, mock_prompt):
        """Test handle_error returns retry action."""
        mock_prompt.return_value = "1"  # First option (retry)

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        error = ValueError("Test error")

        action = workflow.handle_error(error)

        assert action == RecoveryAction.RETRY

    @patch("ei_cli.workflow.interactive.Prompt.ask")
    def test_handle_error_interactive_abort(self, mock_prompt):
        """Test handle_error returns abort action."""
        mock_prompt.return_value = "3"  # Third option (abort)

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        error = ValueError("Test error")

        action = workflow.handle_error(error)

        assert action == RecoveryAction.ABORT

    def test_handle_error_headless(self):
        """Test handle_error in headless mode always aborts."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        error = ValueError("Test error")

        action = workflow.handle_error(error)

        assert action == RecoveryAction.ABORT

    @patch("ei_cli.workflow.interactive.Prompt.ask")
    def test_prompt_choice_interactive(self, mock_prompt):
        """Test prompt_choice in interactive mode."""
        mock_prompt.return_value = "2"

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        choice = workflow.prompt_choice(
            "Select option",
            ["Option 1", "Option 2", "Option 3"],
        )

        assert choice == "Option 2"

    def test_prompt_choice_headless_with_default(self):
        """Test prompt_choice in headless mode uses default."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        choice = workflow.prompt_choice(
            "Select option",
            ["Option 1", "Option 2", "Option 3"],
            default="Option 2",
        )

        assert choice == "Option 2"

    def test_prompt_choice_headless_no_default(self):
        """Test prompt_choice in headless mode uses first option."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        choice = workflow.prompt_choice(
            "Select option",
            ["Option 1", "Option 2", "Option 3"],
        )

        assert choice == "Option 1"

    @patch("ei_cli.workflow.interactive.Prompt.ask")
    def test_prompt_input_interactive(self, mock_prompt):
        """Test prompt_input in interactive mode."""
        mock_prompt.return_value = "user input"

        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        result = workflow.prompt_input("Enter value")

        assert result == "user input"

    def test_prompt_input_headless_with_default(self):
        """Test prompt_input in headless mode uses default."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        result = workflow.prompt_input("Enter value", default="default value")

        assert result == "default value"

    def test_prompt_input_headless_no_default_raises(self):
        """Test prompt_input in headless mode without default raises."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)

        with pytest.raises(ValueError, match="No default provided"):
            workflow.prompt_input("Enter value")

    @patch("ei_cli.workflow.interactive.console")
    def test_show_progress_step(self, mock_console):
        """Test show_progress_step displays correctly."""
        workflow = InteractiveWorkflow()
        workflow.show_progress_step("Download file", 1, 3)

        mock_console.print.assert_called_once()

    @patch("ei_cli.workflow.interactive.console")
    def test_show_completion(self, mock_console):
        """Test show_completion displays message."""
        workflow = InteractiveWorkflow()
        workflow.show_completion("All done!")

        assert mock_console.print.call_count >= 1

    @patch("ei_cli.workflow.interactive.console")
    def test_show_completion_with_details(self, mock_console):
        """Test show_completion with details."""
        workflow = InteractiveWorkflow()
        workflow.show_completion(
            "All done!",
            details={"files": 3, "size": "10MB"},
        )

        assert mock_console.print.call_count >= 2

    @patch("ei_cli.workflow.interactive.console")
    def test_show_warning_interactive(self, mock_console):
        """Test show_warning in interactive mode."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        workflow.show_warning("This is a warning")

        mock_console.print.assert_called_once()

    @patch("ei_cli.workflow.interactive.console")
    def test_show_warning_auto_skip(self, mock_console):
        """Test show_warning skips in auto mode."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.AUTO)
        workflow.show_warning("This is a warning", skip_in_auto=True)

        mock_console.print.assert_not_called()

    def test_repr(self):
        """Test string representation."""
        workflow = InteractiveWorkflow(mode=WorkflowMode.INTERACTIVE)
        repr_str = repr(workflow)

        assert "InteractiveWorkflow" in repr_str
        assert "interactive" in repr_str


class TestWithErrorRecovery:
    """Tests for with_error_recovery function."""

    def test_success_no_retry(self):
        """Test function succeeds without retry."""
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return "success"

        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        result = with_error_recovery(func, max_retries=3, workflow=workflow)

        assert result == "success"
        assert call_count == 1

    @patch("ei_cli.workflow.interactive.InteractiveWorkflow.handle_error")
    def test_retry_then_success(self, mock_handle_error):
        """Test function fails once then succeeds."""
        mock_handle_error.return_value = RecoveryAction.RETRY

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success"

        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)
        result = with_error_recovery(func, max_retries=3, workflow=workflow)

        assert result == "success"
        assert call_count == 2

    @patch("ei_cli.workflow.interactive.InteractiveWorkflow.handle_error")
    def test_abort_on_error(self, mock_handle_error):
        """Test function aborts on error."""
        mock_handle_error.return_value = RecoveryAction.ABORT

        def func():
            raise ValueError("Error")

        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)

        with pytest.raises(ValueError, match="Error"):
            with_error_recovery(func, max_retries=3, workflow=workflow)

    def test_max_retries_exhausted(self):
        """Test all retries exhausted raises error."""
        def func():
            raise ValueError("Always fails")

        workflow = InteractiveWorkflow(mode=WorkflowMode.HEADLESS)

        with pytest.raises(ValueError, match="Always fails"):
            with_error_recovery(func, max_retries=2, workflow=workflow)
