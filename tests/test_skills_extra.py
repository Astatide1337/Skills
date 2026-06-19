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
allowed-tools:
  - skills_list
tags:
  - test
author: agent
license: MIT
compatibility: ">=0.1.0"
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
        required_errors = [e for e in errors if "required" in e]
        assert any("name" in e for e in required_errors)

    def test_missing_description_field(self, tmp_path):
        skill_dir = tmp_path / "no-desc-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: no-desc-skill
metadata:
  version: "1.0.0"
---

Content
""")
        errors = validate_skills(tmp_path)
        required_errors = [e for e in errors if "required" in e]
        assert any("description" in e for e in required_errors)

    def test_missing_version_required(self, tmp_path):
        skill_dir = tmp_path / "no-version-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: no-version-skill
description: No version
---

Content
""")
        errors = validate_skills(tmp_path)
        required_errors = [e for e in errors if "required" in e]
        assert any("version" in e for e in required_errors)

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

    def test_risk_level_valid(self, tmp_path):
        skill_dir = tmp_path / "risk-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: risk-skill
description: test
metadata:
  version: "1.0.0"
risk_level: medium
---

Content
""")
        errors = validate_skills(tmp_path)
        required_errors = [e for e in errors if "risk_level" in e.lower()]
        assert required_errors == []

    def test_risk_level_invalid(self, tmp_path):
        skill_dir = tmp_path / "bad-risk"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: bad-risk
description: test
metadata:
  version: "1.0.0"
risk_level: critical
---

Content
""")
        errors = validate_skills(tmp_path)
        assert any("risk_level" in e for e in errors)

    def test_recommended_field_warnings(self, tmp_path):
        skill_dir = tmp_path / "minimal-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: minimal-skill
description: bare minimum
metadata:
  version: "1.0.0"
---

Content
""")
        errors = validate_skills(tmp_path)
        warnings = [e for e in errors if "recommended" in e]
        assert len(warnings) > 0

    def test_fixtures_valid_skill(self):
        from skills_gateway.skills import validate_skills
        errors = validate_skills(Path("tests/fixtures/skills"))
        valid_errors = [e for e in errors if e.startswith("valid-skill:") and "required" in e]
        assert valid_errors == []

    def test_fixtures_invalid_skill(self):
        from skills_gateway.skills import validate_skills
        errors = validate_skills(Path("tests/fixtures/skills"))
        invalid_errors = [e for e in errors if "invalid-skill" in e]
        assert len(invalid_errors) > 0

    def test_multiple_skills_mixed(self, tmp_path):
        good = tmp_path / "good-skill"
        good.mkdir()
        (good / "SKILL.md").write_text("---\nname: good-skill\ndescription: good\nmetadata:\n  version: \"1.0\"\n---\n")

        bad = tmp_path / "bad-skill"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: bad-skill\n---\n")

        skip = tmp_path / "skip-dir"
        skip.mkdir()

        errors = validate_skills(tmp_path)
        required_errors = [e for e in errors if "required" in e]
        assert len(required_errors) >= 2
        assert any("bad-skill" in e for e in required_errors)


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
