"""Interactive workflow management with user prompts and error recovery."""

import os
import sys
from enum import Enum
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()


class WorkflowMode(Enum):
    """Workflow execution mode."""

    INTERACTIVE = "interactive"  # Ask user for input
    AUTO = "auto"  # Use defaults, no prompts
    HEADLESS = "headless"  # Non-interactive (CI/CD)


class RecoveryAction(Enum):
    """Available recovery actions for errors."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    CONTINUE = "continue"


class InteractiveWorkflow:
    """Interactive workflow with user prompts and error recovery."""

    def __init__(self, mode: WorkflowMode | None = None) -> None:
        """
        Initialize interactive workflow.

        Args:
            mode: Workflow mode (auto-detected if None)
        """
        self.mode = mode or self._detect_mode()

    def _detect_mode(self) -> WorkflowMode:
        """
        Auto-detect workflow mode from environment.

        Returns:
            Detected workflow mode
        """
        # Check if running in CI/CD
        ci_vars = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI"]
        if any(os.getenv(var) for var in ci_vars):
            return WorkflowMode.HEADLESS

        # Check if terminal is interactive
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return WorkflowMode.HEADLESS

        # Default to interactive
        return WorkflowMode.INTERACTIVE

    def is_interactive(self) -> bool:
        """Check if workflow is in interactive mode."""
        return self.mode == WorkflowMode.INTERACTIVE

    def confirm_step(
        self,
        step_name: str,
        details: str = "",
        default: bool = True,
        expensive: bool = False,
    ) -> bool:
        """
        Confirm before executing a step.

        Args:
            step_name: Name of the step to execute
            details: Additional details about the step
            default: Default choice if not interactive
            expensive: If True, emphasize cost/time in prompt

        Returns:
            True if user wants to proceed
        """
        # Non-interactive mode: use default
        if not self.is_interactive():
            return default

        # Show step information
        console.print(f"\n[cyan]{'💰' if expensive else '➡️'}  About to: {step_name}[/cyan]")

        if details:
            console.print(f"[dim]{details}[/dim]")

        if expensive:
            console.print(
                "[yellow]⚠️  This operation may be time-consuming or costly[/yellow]",
            )

        # Ask for confirmation
        return Confirm.ask("Proceed?", default=default)

    def handle_error(
        self,
        error: Exception,
        context: str = "",
        recovery_options: list[RecoveryAction] | None = None,
    ) -> RecoveryAction:
        """
        Present error and recovery options to user.

        Args:
            error: The exception that occurred
            context: Context about where error occurred
            recovery_options: Available recovery actions (default: all)

        Returns:
            Selected recovery action
        """
        if recovery_options is None:
            recovery_options = [
                RecoveryAction.RETRY,
                RecoveryAction.SKIP,
                RecoveryAction.ABORT,
            ]

        # Show error
        console.print(f"\n[red bold]✗ Error: {type(error).__name__}[/red bold]")
        console.print(f"[red]{error}[/red]")

        if context:
            console.print(f"\n[dim]Context: {context}[/dim]")

        # Non-interactive mode: abort on error
        if not self.is_interactive():
            console.print("[yellow]Non-interactive mode: aborting[/yellow]")
            return RecoveryAction.ABORT

        # Show recovery options
        console.print("\n[yellow]What would you like to do?[/yellow]")

        options_map = {
            RecoveryAction.RETRY: "Retry the operation",
            RecoveryAction.SKIP: "Skip this step and continue",
            RecoveryAction.ABORT: "Abort the workflow",
            RecoveryAction.CONTINUE: "Continue despite error",
        }

        choices = []
        for i, action in enumerate(recovery_options, 1):
            description = options_map.get(action, action.value)
            console.print(f"  {i}. {description}")
            choices.append(str(i))

        # Get user choice
        choice = Prompt.ask(
            "Choose option",
            choices=choices,
            default="1",
        )

        selected_action = recovery_options[int(choice) - 1]

        # Show selected action
        action_name = options_map.get(selected_action, selected_action.value)
        console.print(f"[cyan]→ {action_name}[/cyan]")

        return selected_action

    def prompt_choice(
        self,
        question: str,
        choices: list[str],
        default: str | None = None,
    ) -> str:
        """
        Prompt user to choose from options.

        Args:
            question: Question to ask
            choices: List of valid choices
            default: Default choice if not interactive

        Returns:
            Selected choice
        """
        # Non-interactive mode: use default or first option
        if not self.is_interactive():
            return default or choices[0]

        console.print(f"\n[cyan]{question}[/cyan]")
        for i, choice in enumerate(choices, 1):
            console.print(f"  {i}. {choice}")

        choice_idx = Prompt.ask(
            "Select option",
            choices=[str(i) for i in range(1, len(choices) + 1)],
            default="1",
        )

        return choices[int(choice_idx) - 1]

    def prompt_input(
        self,
        question: str,
        default: str | None = None,
        password: bool = False,
    ) -> str:
        """
        Prompt user for text input.

        Args:
            question: Question to ask
            default: Default value if not interactive
            password: If True, hide input (for passwords)

        Returns:
            User input
        """
        # Non-interactive mode: use default or empty string
        if not self.is_interactive():
            if default is not None:
                return default
            raise ValueError(f"No default provided for: {question}")

        return Prompt.ask(
            question,
            default=default,
            password=password,
        )

    def show_progress_step(
        self,
        step_name: str,
        step_num: int,
        total_steps: int,
    ) -> None:
        """
        Show progress indicator for current step.

        Args:
            step_name: Name of the current step
            step_num: Current step number (1-indexed)
            total_steps: Total number of steps
        """
        console.print(
            f"\n[bold cyan]Step {step_num}/{total_steps}:[/bold cyan] {step_name}",
        )

    def show_completion(
        self,
        message: str = "Workflow completed successfully!",
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Show workflow completion message.

        Args:
            message: Completion message
            details: Optional details to show
        """
        console.print(f"\n[green bold]✓ {message}[/green bold]")

        if details:
            console.print("\n[cyan]Details:[/cyan]")
            for key, value in details.items():
                console.print(f"  {key}: {value}")

    def show_warning(
        self,
        message: str,
        skip_in_auto: bool = True,
    ) -> None:
        """
        Show warning message.

        Args:
            message: Warning message
            skip_in_auto: If True, skip in auto mode
        """
        if skip_in_auto and not self.is_interactive():
            return

        console.print(f"\n[yellow]⚠️  {message}[/yellow]")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"InteractiveWorkflow(mode={self.mode.value})"


# Convenience function for common error handling pattern

def with_error_recovery(
    func: callable,
    max_retries: int = 3,
    workflow: InteractiveWorkflow | None = None,
) -> Any:
    """
    Execute function with automatic error recovery.

    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        workflow: Workflow instance (created if None)

    Returns:
        Function result

    Raises:
        Exception: If all retries exhausted or user aborts
    """
    if workflow is None:
        workflow = InteractiveWorkflow()

    attempts = 0
    while attempts < max_retries:
        try:
            return func()
        except Exception as e:
            attempts += 1

            # Determine recovery options based on attempts left
            recovery_options = [RecoveryAction.RETRY, RecoveryAction.ABORT]
            if attempts >= max_retries:
                recovery_options = [RecoveryAction.ABORT]

            action = workflow.handle_error(
                error=e,
                context=f"Attempt {attempts}/{max_retries}",
                recovery_options=recovery_options,
            )

            if action == RecoveryAction.ABORT:
                raise
            if action == RecoveryAction.RETRY:
                continue
            raise

    raise RuntimeError(f"Max retries ({max_retries}) exceeded")
