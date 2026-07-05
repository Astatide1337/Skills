import json
import pytest
from pathlib import Path

from skills_gateway.skills import parse_skill_frontmatter, get_skills_catalog, get_skill_file_tree, normalize_skill_manifest


@pytest.fixture
def skills_dir(tmp_path):
    skill_a = tmp_path / "skill-a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(
        "---\n"
        "name: Skill A\n"
        "description: A test skill\n"
        "metadata:\n"
        "  version: 1.0.0\n"
        "---\n"
        "Body content\n"
    )
    (skill_a / "helper.py").write_text("print('hello')")

    skill_b = tmp_path / "skill-b"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(
        "---\n"
        "name: Skill B\n"
        "description: Another test skill\n"
        "---\n"
        "More content\n"
    )

    empty_dir = tmp_path / "empty-skill"
    empty_dir.mkdir()

    return tmp_path


class TestParseSkillFrontmatter:
    def test_valid_frontmatter(self, skills_dir):
        result = parse_skill_frontmatter(skills_dir / "skill-a")
        assert result is not None
        assert result["name"] == "Skill A"
        assert result["description"] == "A test skill"
        assert result["metadata"]["version"] == "1.0.0"

    def test_no_frontmatter_markers(self, tmp_path):
        d = tmp_path / "noskill"
        d.mkdir()
        (d / "SKILL.md").write_text("Just some text\n")
        assert parse_skill_frontmatter(d) is None

    def test_no_skill_md(self, tmp_path):
        d = tmp_path / "nomd"
        d.mkdir()
        assert parse_skill_frontmatter(d) is None

    def test_minimal_frontmatter(self, skills_dir):
        result = parse_skill_frontmatter(skills_dir / "skill-b")
        assert result is not None
        assert result["name"] == "Skill B"

    def test_empty_dir(self, skills_dir):
        result = parse_skill_frontmatter(skills_dir / "empty-skill")
        assert result is None


class TestGetSkillsCatalog:
    def test_returns_named_skills(self, skills_dir):
        catalog = get_skills_catalog(skills_dir)
        names = {s["name"] for s in catalog}
        assert names == {"Skill A", "Skill B"}

    def test_skips_dirs_without_name(self, skills_dir):
        catalog = get_skills_catalog(skills_dir)
        for s in catalog:
            assert s["name"]

    def test_nonexistent_dir(self, tmp_path):
        catalog = get_skills_catalog(tmp_path / "nope")
        assert catalog == []

    def test_catalog_fields(self, skills_dir):
        catalog = get_skills_catalog(skills_dir)
        skill_a = next(s for s in catalog if s["name"] == "Skill A")
        assert skill_a["description"] == "A test skill"
        assert skill_a["version"] == "1.0.0"
        assert skill_a["path"] == "skill-a"



    def test_catalog_normalizes_canonical_fields(self, skills_dir):
        catalog = get_skills_catalog(skills_dir)
        skill_a = next(s for s in catalog if s["id"] == "skill-a")
        assert skill_a["entrypoint"] == "SKILL.md"
        assert skill_a["risk_level"] == "low"
        assert skill_a["allowed_tools"] == []

    def test_normalize_supports_top_level_version_and_entrypoint(self, tmp_path):
        d = tmp_path / "canonical-skill"
        d.mkdir()
        (d / "README.md").write_text("entry")
        frontmatter = {
            "name": "canonical-skill",
            "description": "desc",
            "version": "2.0.0",
            "entrypoint": "README.md",
        }
        manifest = normalize_skill_manifest(d, frontmatter)
        assert manifest["id"] == "canonical-skill"
        assert manifest["version"] == "2.0.0"
        assert manifest["entrypoint"] == "README.md"


class TestGetSkillFileTree:
    def test_lists_files(self, skills_dir):
        tree = get_skill_file_tree(skills_dir / "skill-a")
        assert "SKILL.md" in tree
        assert "helper.py" in tree

    def test_nonexistent_dir(self, tmp_path):
        tree = get_skill_file_tree(tmp_path / "nope")
        assert tree == []

    def test_sorted_order(self, skills_dir):
        tree = get_skill_file_tree(skills_dir / "skill-a")
        assert tree == sorted(tree)
