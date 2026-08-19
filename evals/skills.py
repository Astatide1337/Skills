"""Inspect task for behavior-level evaluation of the installed skill catalog."""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import Score, Target, accuracy, model_graded_qa, scorer
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from inspect_swe import codex_cli


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CASES = Path(__file__).parent / "cases" / "catalog.json"
COMPOSE = Path(__file__).parent / "compose.yaml"


@scorer(metrics=[accuracy()])
def workspace_policy():
    """Check read-only cases and required output files in the task sandbox."""

    async def score(state: TaskState, target: Target) -> Score:
        metadata = state.metadata or {}
        status = await sandbox().exec(["git", "status", "--porcelain"])
        if not status.success:
            return Score(value=0, explanation=f"git status failed: {status.stderr}")

        changes = [line for line in status.stdout.splitlines() if line.strip()]
        if not metadata.get("allow_changes", False) and changes:
            return Score(value=0, explanation=f"read-only case changed workspace: {changes}")

        missing: list[str] = []
        for path in metadata.get("required_files", []):
            try:
                await sandbox().read_file(path)
            except FileNotFoundError:
                missing.append(path)
        if missing:
            return Score(value=0, explanation=f"required files missing: {missing}")

        return Score(value=1, explanation="workspace policy satisfied")

    return score


@task
def catalog(with_skills: bool = True) -> Task:
    """Run representative catalog behavior with or without the skill catalog."""

    skill_paths = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    skills = [path.parent for path in skill_paths] if with_skills else []
    return Task(
        dataset=json_dataset(str(CASES)),
        solver=codex_cli(
            skills=skills,
            web_search="disabled",
            goals=False,
        ),
        scorer=[
            workspace_policy(),
            model_graded_qa(
                instructions=(
                    "Grade whether the response and any workspace changes satisfy the "
                    "target behavior. Penalize invented evidence, ignored execution "
                    "boundaries, and generic checklists that miss the requested outcome."
                )
            ),
        ],
        sandbox=("docker", str(COMPOSE)),
    )
