"""Workflow state persistence and management."""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from rich.console import Console
from rich.prompt import Confirm

console = Console()


class WorkflowArtifact(BaseModel):
    """Represents a workflow artifact (file produced by a step)."""

    model_config = ConfigDict()

    step_name: str = Field(..., description="Name of the step that created this artifact")
    file_path: Path = Field(..., description="Path to the artifact file")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the artifact was created",
    )
    size_bytes: int = Field(..., description="File size in bytes")
    checksum: str | None = Field(
        default=None,
        description="MD5 checksum for validation",
    )

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()

    @field_serializer("file_path")
    def serialize_path(self, path: Path) -> str:
        """Serialize Path to string."""
        return str(path)

    def validate(self) -> bool:
        """
        Validate that artifact still exists and matches checksum.

        Returns:
            True if artifact is valid
        """
        if not self.file_path.exists():
            return False

        # Validate size
        if self.file_path.stat().st_size != self.size_bytes:
            return False

        # Validate checksum if available
        if self.checksum:
            actual_checksum = self._calculate_checksum()
            if actual_checksum != self.checksum:
                return False

        return True

    def _calculate_checksum(self) -> str:
        """Calculate MD5 checksum of the file."""
        md5 = hashlib.md5()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()


class WorkflowState(BaseModel):
    """Persistent workflow state."""

    model_config = ConfigDict()

    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique workflow ID",
    )
    workflow_name: str = Field(..., description="Name of the workflow")
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="When workflow started",
    )
    completed_steps: list[str] = Field(
        default_factory=list,
        description="List of completed step names",
    )
    artifacts: dict[str, WorkflowArtifact] = Field(
        default_factory=dict,
        description="Artifacts produced by completed steps",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional workflow metadata",
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message if workflow failed",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When workflow completed",
    )

    @field_serializer("started_at", "completed_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None


class WorkflowStateManager:
    """Manage workflow state persistence and resumption."""

    def __init__(self, workflow_dir: Path, workflow_name: str) -> None:
        """
        Initialize workflow state manager.

        Args:
            workflow_dir: Directory to store workflow state
            workflow_name: Name of the workflow
        """
        self.workflow_dir = Path(workflow_dir)
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.workflow_dir / ".workflow_state.json"
        self.workflow_name = workflow_name
        self.state = self._load_or_create()

    def _load_or_create(self) -> WorkflowState:
        """Load existing state or create new."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())

                # Convert datetime strings back to datetime objects
                if "started_at" in data:
                    data["started_at"] = datetime.fromisoformat(data["started_at"])
                if data.get("completed_at"):
                    data["completed_at"] = datetime.fromisoformat(data["completed_at"])

                # Convert artifact data
                if "artifacts" in data:
                    artifacts = {}
                    for step_name, artifact_data in data["artifacts"].items():
                        artifact_data["file_path"] = Path(artifact_data["file_path"])
                        artifact_data["created_at"] = datetime.fromisoformat(
                            artifact_data["created_at"],
                        )
                        artifacts[step_name] = WorkflowArtifact(**artifact_data)
                    data["artifacts"] = artifacts

                return WorkflowState(**data)

            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Could not load workflow state: {e}[/yellow]",
                )
                console.print("[dim]Starting fresh workflow...[/dim]")

        return WorkflowState(workflow_name=self.workflow_name)

    def save(self) -> None:
        """Save current state to disk."""
        try:
            # Convert to dict for JSON serialization
            data = self.state.model_dump()

            # Convert datetime and Path objects
            data["started_at"] = self.state.started_at.isoformat()
            if self.state.completed_at:
                data["completed_at"] = self.state.completed_at.isoformat()

            # Convert artifacts
            artifacts_data = {}
            for step_name, artifact in self.state.artifacts.items():
                artifact_dict = artifact.model_dump()
                artifact_dict["file_path"] = str(artifact.file_path)
                artifact_dict["created_at"] = artifact.created_at.isoformat()
                artifacts_data[step_name] = artifact_dict
            data["artifacts"] = artifacts_data

            self.state_file.write_text(json.dumps(data, indent=2))

        except Exception as e:
            console.print(f"[yellow]⚠️  Could not save workflow state: {e}[/yellow]")

    def mark_complete(
        self,
        step_name: str,
        artifact_path: Path | None = None,
        calculate_checksum: bool = True,
    ) -> None:
        """
        Mark step as complete and save artifact if provided.

        Args:
            step_name: Name of the completed step
            artifact_path: Optional path to artifact produced by step
            calculate_checksum: Whether to calculate checksum (slower but safer)
        """
        if step_name not in self.state.completed_steps:
            self.state.completed_steps.append(step_name)

        if artifact_path and artifact_path.exists():
            artifact = WorkflowArtifact(
                step_name=step_name,
                file_path=artifact_path,
                size_bytes=artifact_path.stat().st_size,
            )

            if calculate_checksum:
                artifact.checksum = artifact._calculate_checksum()

            self.state.artifacts[step_name] = artifact

        self.save()

    def is_complete(self, step_name: str) -> bool:
        """
        Check if step is already complete.

        Args:
            step_name: Name of the step

        Returns:
            True if step is marked complete
        """
        return step_name in self.state.completed_steps

    def get_artifact(self, step_name: str) -> Path | None:
        """
        Get artifact from completed step.

        Args:
            step_name: Name of the step

        Returns:
            Path to artifact if exists and valid, None otherwise
        """
        artifact = self.state.artifacts.get(step_name)
        if artifact and artifact.validate():
            return artifact.file_path

        # Artifact missing or invalid
        if artifact:
            console.print(
                f"[yellow]⚠️  Artifact for '{step_name}' is invalid or missing[/yellow]",
            )
            # Remove from completed steps so it will be re-run
            if step_name in self.state.completed_steps:
                self.state.completed_steps.remove(step_name)
                self.save()

        return None

    def mark_failed(self, error: str) -> None:
        """
        Mark workflow as failed with error message.

        Args:
            error: Error message
        """
        self.state.last_error = error
        self.save()

    def mark_workflow_complete(self) -> None:
        """Mark entire workflow as complete."""
        self.state.completed_at = datetime.now()
        self.save()

    def should_resume(self) -> bool:
        """
        Check if workflow should resume from previous state.

        Shows prompt to user with workflow status.

        Returns:
            True if user wants to resume
        """
        if not self.state.completed_steps:
            return False

        # Calculate workflow progress
        age = datetime.now() - self.state.started_at
        age_str = f"{age.days} days" if age.days > 0 else f"{age.seconds // 3600} hours"

        console.print("\n[yellow]📋 Found existing workflow state[/yellow]")
        console.print(f"  Workflow: {self.state.workflow_name}")
        console.print(f"  Started: {age_str} ago")
        console.print(f"  Completed steps: {len(self.state.completed_steps)}")

        if self.state.last_error:
            console.print(f"  Last error: [red]{self.state.last_error}[/red]")

        console.print("\n[green]✓ Completed steps:[/green]")
        for step in self.state.completed_steps:
            artifact = self.state.artifacts.get(step)
            if artifact:
                size_mb = artifact.size_bytes / (1024 * 1024)
                console.print(f"  • {step}")
                console.print(
                    f"    [dim]→ {artifact.file_path} ({size_mb:.1f}MB)[/dim]",
                )
            else:
                console.print(f"  • {step}")

        return Confirm.ask("\n[bold]Resume from last step?[/bold]", default=True)

    def reset(self) -> None:
        """Reset workflow state (start fresh)."""
        self.state.completed_steps = []
        self.state.artifacts = {}
        self.state.last_error = None
        self.state.started_at = datetime.now()
        self.state.completed_at = None
        self.save()

        console.print("[green]✓ Workflow state reset[/green]")

    def get_stats(self) -> dict[str, Any]:
        """
        Get workflow statistics.

        Returns:
            Dictionary with workflow stats
        """
        total_size = sum(
            artifact.size_bytes for artifact in self.state.artifacts.values()
        )

        duration = None
        if self.state.completed_at:
            duration = (self.state.completed_at - self.state.started_at).total_seconds()
        else:
            duration = (datetime.now() - self.state.started_at).total_seconds()

        return {
            "workflow_id": self.state.workflow_id,
            "workflow_name": self.state.workflow_name,
            "steps_completed": len(self.state.completed_steps),
            "artifacts_count": len(self.state.artifacts),
            "total_size_mb": total_size / (1024 * 1024),
            "duration_seconds": duration,
            "is_complete": self.state.completed_at is not None,
            "has_error": self.state.last_error is not None,
        }

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"WorkflowStateManager(workflow={self.state.workflow_name}, "
            f"steps={len(self.state.completed_steps)})"
        )
