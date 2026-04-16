import os
from pathlib import Path
from app.agent.tools.markdown_loader import load_skills_from_directory

def test_load_skills(tmp_path):
    d = tmp_path / "test_skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: my_test\ndescription: test desc\n---\nbody text")
    
    tools = load_skills_from_directory(str(tmp_path))
    assert len(tools) == 1
    assert tools[0].name == "my_test"
    assert tools[0].description == "test desc"
