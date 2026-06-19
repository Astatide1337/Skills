import json
import pytest
from pathlib import Path

from skills_gateway.skills import (
    parse_skill_frontmatter,
    get_skills_catalog,
    get_skill_file_tree,
    validate_skills,
)


class TestValidateSkills:
    def test_no_errors_valid_skill(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: A test skill
metadata:
  version: "1.0.0"
---

Content here
""")
        errors = validate_skills(tmp_path)
        assert errors == []

    def test_missing_name_field(self, tmp_path):
        skill_dir = tmp_path / "no-name-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: No name
metadata:
  version: "1.0.0"
---

Content
""")
        errors = validate_skills(tmp_path)
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_missing_version_recommended(self, tmp_path):
        skill_dir = tmp_path / "no-version-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: no-version-skill
description: No version
---

Content
""")
        errors = validate_skills(tmp_path)
        assert len(errors) == 1
        assert "version" in errors[0]

    def test_invalid_yaml_frontmatter(self, tmp_path):
        skill_dir = tmp_path / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
: invalid yaml [[[
---

Content
""")
        errors = validate_skills(tmp_path)
        assert len(errors) == 1
        assert "invalid" in errors[0].lower()

    def test_skips_dirs_without_skill_md(self, tmp_path):
        (tmp_path / "not-a-skill").mkdir()
        (tmp_path / ".hidden").mkdir()
        errors = validate_skills(tmp_path)
        assert errors == []

    def test_nonexistent_dir(self, tmp_path):
        errors = validate_skills(tmp_path / "nonexistent")
        assert errors == []

    def test_multiple_skills_mixed(self, tmp_path):
        good = tmp_path / "good-skill"
        good.mkdir()
        (good / "SKILL.md").write_text("---\nname: good-skill\nmetadata:\n  version: \"1.0\"\n---\n")

        bad = tmp_path / "bad-skill"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: bad-skill\n---\n")

        skip = tmp_path / "skip-dir"
        skip.mkdir()

        errors = validate_skills(tmp_path)
        assert len(errors) == 1
        assert "bad-skill" in errors[0]


class TestGetSkillsCatalogWithProfile:
    def test_catalog_returns_all(self, tmp_path):
        for name in ("skill-a", "skill-b"):
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: desc\n---\n")
        catalog = get_skills_catalog(tmp_path)
        assert len(catalog) == 2

    def test_catalog_skips_no_name(self, tmp_path):
        d = tmp_path / "unnamed"
        d.mkdir()
        (d / "SKILL.md").write_text("---\ndescription: no name\n---\n")
        catalog = get_skills_catalog(tmp_path)
        assert len(catalog) == 0

    def test_catalog_fields_have_path(self, tmp_path):
        d = tmp_path / "pathed-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: pathed-skill\n---\n")
        catalog = get_skills_catalog(tmp_path)
        assert catalog[0]["path"] == "pathed-skill"
