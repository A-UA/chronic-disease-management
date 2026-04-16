import os
from pathlib import Path
import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class GenericSkillInput(BaseModel):
    query: str = Field(description="The contextual query for this skill to act upon")

def markdown_skill_factory(name: str, description: str, instructions: str):
    def _run_skill(query: str) -> str:
        # In a real environment, we'd invoke sub-chains, 
        # but the standard agentskills.io way passes instructions as context back to the agent:
        return f"=== SKILL INSTRUCTIONS ===\n{instructions}\n=== END SKILL/APPLY TO ===\nQuery: {query}"
        
    return StructuredTool.from_function(
        func=_run_skill,
        name=name,
        description=description,
        args_schema=GenericSkillInput
    )

def load_skills_from_directory(directory: str) -> list[StructuredTool]:
    tools = []
    base_path = Path(directory)
    if not base_path.exists():
        return tools
        
    for skill_dir in base_path.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    tools.append(
                        markdown_skill_factory(
                            name=frontmatter.get("name", skill_dir.name),
                            description=frontmatter.get("description", ""),
                            instructions=body
                        )
                    )
    return tools
