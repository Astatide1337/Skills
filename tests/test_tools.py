import json

import pytest

from skills_gateway.config import GatewayConfig, ProfileDef, SkillsConfig
from skills_gateway.tools import (
    inspect_skill_manifest,
    read_skill_file,
    search_skill_manifests,
)


@pytest.fixture
def skills_dir(tmp_path):
    public = tmp_path / "public-skill"
    public.mkdir()
    (public / "SKILL.md").write_text("""---
name: Public Skill
description: Public searchable skill
metadata:
  version: "1.0.0"
risk_level: low
---
# Public
""")

    private = tmp_path / "private-skill"
    private.mkdir()
    (private / "SKILL.md").write_text("""---
name: Private Skill
description: Private searchable skill
metadata:
  version: "1.0.0"
risk_level: medium
---
# Private
""")
    return tmp_path


def _cfg(skills_dir):
    return GatewayConfig(skills=SkillsConfig(dir=str(skills_dir)))


class TestSkillTools:
    def test_skills_search_returns_ids_and_paths(self, skills_dir):
        data = search_skill_manifests(skills_dir, _cfg(skills_dir), "public")
        assert data[0]["id"] == "public-skill"
        assert data[0]["path"] == "public-skill"
        assert data[0]["risk_level"] == "low"

    def test_skills_inspect_returns_canonical_manifest(self, skills_dir):
        data = inspect_skill_manifest(skills_dir, _cfg(skills_dir), "public-skill")
        assert data["manifest"]["id"] == "public-skill"
        assert data["manifest"]["entrypoint"] == "SKILL.md"
        assert "SKILL.md" in data["file_tree"]

    def test_skill_read_respects_active_profile(self, skills_dir):
        cfg = GatewayConfig(
            skills=SkillsConfig(dir=str(skills_dir)),
            profiles={"dev": ProfileDef(skills=["public-skill"])},
            active_profile="dev",
        )
        result = read_skill_file(skills_dir, cfg, "private-skill/SKILL.md")
        data = json.loads(result)
        assert data["error"]["code"] == "not_in_active_profile"

    def test_skill_read_rejects_traversal(self, skills_dir):
        result = read_skill_file(skills_dir, _cfg(skills_dir), "../secret.txt")
        data = json.loads(result)
        assert data["error"]["code"] == "invalid_path"
