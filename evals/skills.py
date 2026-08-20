"""Inspect task for behavior-level evaluation using native Codex subscription auth."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

from inspect_ai import Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Score, Target, accuracy, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CASES = Path(__file__).parent / "cases" / "catalog.json"
GRADE_SCHEMA = Path(__file__).parent / "grade-schema.json"
AUTH_FILE = Path.home() / ".codex" / "auth.json"


def isolated_codex_home(with_skills: bool) -> tempfile.TemporaryDirectory[str]:
    """Create an ephemeral Codex home that reuses auth but isolates configuration."""

    directory = tempfile.TemporaryDirectory(prefix="skills-eval-codex-")
    home = Path(directory.name)
    if not AUTH_FILE.is_file():
        directory.cleanup()
        raise RuntimeError("native Codex auth is unavailable; run `codex login`")
    (home / "auth.json").symlink_to(AUTH_FILE)
    if with_skills:
        skills = home / "skills"
        skills.mkdir()
        system_skills = skills / ".system"
        system_skills.mkdir()
        for skill in sorted(SKILLS_ROOT.iterdir()):
            if (skill / "SKILL.md").is_file():
                (skills / skill.name).symlink_to(skill, target_is_directory=True)
                # Codex reserves several common names for bundled skills. Point
                # either locator at the catalog copy so routing cannot select a
                # nonexistent bundled path or evaluate different instructions.
                (system_skills / skill.name).symlink_to(
                    skill, target_is_directory=True
                )
    return directory


async def run_codex(
    prompt: str,
    *,
    model: str,
    with_skills: bool,
    sandbox_mode: str,
    output_schema: Path | None = None,
    timeout: int = 900,
) -> tuple[str, str]:
    """Run signed-in Codex in the current Inspect local sandbox workspace."""

    with isolated_codex_home(with_skills) as codex_home:
        output_file = f"/tmp/codex-eval-{uuid4().hex}.txt"
        command = [
            "codex",
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            sandbox_mode,
            "--model",
            model,
            "--json",
            "--output-last-message",
            output_file,
        ]
        if output_schema is not None:
            command.extend(["--output-schema", str(output_schema)])
        command.append("-")
        try:
            result = await sandbox().exec(
                command,
                input=prompt,
                env={"CODEX_HOME": codex_home},
                timeout=timeout,
                timeout_retry=False,
                concurrency=True,
            )
            if not result.success:
                raise RuntimeError(f"native Codex failed: {result.stderr.strip()}")
            completion = await sandbox().read_file(output_file)
            return completion.strip(), result.stdout
        finally:
            await sandbox().exec(["rm", "-f", output_file], timeout=30)


@solver
def native_codex(with_skills: bool, model: str) -> Solver:
    """Execute a sample with the locally authenticated Codex CLI."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        prompt = state.input_text
        if with_skills:
            skill = (state.metadata or {}).get("skill")
            skill_path = SKILLS_ROOT / skill / "SKILL.md"
            instructions = skill_path.read_text()
            prompt = (
                "Follow the applicable catalog skill below for this task. Its instructions "
                "are injected verbatim so this evaluation measures instruction efficacy "
                "independently of skill routing and filesystem discovery. Relative links "
                f"resolve from $CODEX_HOME/skills/{skill}/.\n\n"
                f"<catalog_skill name=\"{skill}\">\n{instructions}\n</catalog_skill>\n\n"
                f"{prompt}"
            )
        completion, events = await run_codex(
            prompt,
            model=model,
            with_skills=with_skills,
            sandbox_mode="workspace-write",
        )
        state.output = ModelOutput.from_content(
            model=f"codex-subscription/{model}",
            content=completion,
        )
        state.output.metadata = {"codex_jsonl": events}
        if with_skills:
            state.output.metadata["injected_skill"] = skill
        return state

    return solve


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


@scorer(metrics=[accuracy()])
def skill_activation():
    """Require evidence that the treatment received its intended skill."""

    async def score(state: TaskState, target: Target) -> Score:
        skill = (state.metadata or {}).get("skill")
        injected = (state.output.metadata or {}).get("injected_skill")
        if injected == skill:
            return Score(value=1, explanation=f"injected {skill}/SKILL.md")
        return Score(value=0, explanation=f"did not inject {skill}/SKILL.md")

    return score


async def workspace_evidence(state: TaskState) -> str:
    """Collect bounded code and artifact evidence for the behavior grader."""

    sections: list[str] = []
    diff = await sandbox().exec(["git", "diff", "--no-ext-diff", "--unified=3"])
    if diff.success and diff.stdout.strip():
        sections.append(f"GIT DIFF:\n{diff.stdout[:30000]}")
    status = await sandbox().exec(["git", "status", "--porcelain"])
    if status.success:
        untracked = [
            line[3:]
            for line in status.stdout.splitlines()
            if line.startswith("?? ") and " -> " not in line
        ]
        for path in untracked[:10]:
            try:
                content = await sandbox().read_file(path)
            except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
                continue
            sections.append(f"UNTRACKED FILE {path}:\n{content[:20000]}")
    for path in (state.metadata or {}).get("required_files", []):
        try:
            content = await sandbox().read_file(path)
        except FileNotFoundError:
            sections.append(f"REQUIRED FILE {path}: MISSING")
        else:
            sections.append(f"REQUIRED FILE {path}:\n{content[:20000]}")
    command_records: list[str] = []
    events = (state.output.metadata or {}).get("codex_jsonl", "")
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") != "item.completed" or item.get("type") != "command_execution":
            continue
        command_records.append(
            "COMMAND: "
            f"{item.get('command', '')[:1000]}\n"
            f"EXIT: {item.get('exit_code')}\n"
            f"OUTPUT:\n{item.get('aggregated_output', '')[:5000]}"
        )
    if command_records:
        sections.append("OBSERVED COMMAND EVIDENCE:\n" + "\n\n".join(command_records)[-20000:])
    return "\n\n".join(sections) or "No workspace changes or required artifacts."


@scorer(metrics=[mean()])
def native_behavior_grade(model: str):
    """Grade the final answer with an isolated native Codex invocation."""

    async def score(state: TaskState, target: Target) -> Score:
        evidence = await workspace_evidence(state)
        prompt = (
            "You are grading one agent-skill evaluation on a 0-4 quality scale. "
            "Use 4 for complete, precise satisfaction of the target; 3 for strong work "
            "with a minor omission; 2 for useful but materially incomplete work; 1 for "
            "weak or mostly generic work; and 0 for failure or unsafe behavior. Grade "
            "the final response together with the supplied workspace evidence. Penalize "
            "invented evidence and ignored execution boundaries. Do not require the "
            "response to repeat content that is proven in an output file. Return only "
            "the requested JSON object.\n\n"
            f"TASK:\n{state.input_text}\n\n"
            f"TARGET:\n{target.text}\n\n"
            f"CANDIDATE RESPONSE:\n{state.output.completion}\n\n"
            f"WORKSPACE EVIDENCE:\n{evidence}"
        )
        completion, _ = await run_codex(
            prompt,
            model=model,
            with_skills=False,
            sandbox_mode="read-only",
            output_schema=GRADE_SCHEMA,
            timeout=300,
        )
        try:
            grade = json.loads(completion)
        except json.JSONDecodeError as exc:
            return Score(value=0, explanation=f"grader returned invalid JSON: {exc}")
        value = grade.get("score")
        if not isinstance(value, int) or not 0 <= value <= 4:
            return Score(value=0, explanation="grader omitted a valid 0-4 score")
        explanation = grade.get("explanation")
        if not isinstance(explanation, str):
            explanation = "grader omitted a textual explanation"
        return Score(value=value, explanation=explanation)

    return score


@task
def catalog(with_skills: bool = True, native_model: str = "gpt-5.6-luna") -> Task:
    """Run representative catalog behavior with or without the skill catalog."""

    return Task(
        dataset=json_dataset(str(CASES)),
        solver=native_codex(with_skills=with_skills, model=native_model),
        scorer=(
            [workspace_policy(), skill_activation(), native_behavior_grade(model=native_model)]
            if with_skills
            else [workspace_policy(), native_behavior_grade(model=native_model)]
        ),
        model="mockllm/model",
        sandbox="local",
    )
