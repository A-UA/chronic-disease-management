import os
from pathlib import Path
import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class GenericSkillInput(BaseModel):
    """通用技能输入模型"""
    query: str = Field(description="The contextual query for this skill to act upon")

def markdown_skill_factory(name: str, description: str, instructions: str):
    """动态技能工厂：将 Markdown 指令转换为 LangChain 结构化工具"""
    def _run_skill(query: str) -> str:
        # 在 agent 运行逻辑中，我们将指令作为上下文返回给 Agent，引导其按照 Markdown 定义的流程操作
        return f"=== SKILL INSTRUCTIONS ===\n{instructions}\n=== END SKILL/APPLY TO ===\nQuery: {query}"
        
    return StructuredTool.from_function(
        func=_run_skill,
        name=name,
        description=description,
        args_schema=GenericSkillInput
    )

def load_skills_from_directory(directory: str) -> list[StructuredTool]:
    """从指定目录批量加载 SKILL.md 定义的技能工具"""
    tools = []
    base_path = Path(directory)
    if not base_path.exists():
        return tools
        
    # 遍历 skills 下的每个子目录
    for skill_dir in base_path.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        # 检查是否存在 SKILL.md
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            # 解析 Markdown Frontmatter (YAML 格式)
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    # 读取名称和描述元数据
                    frontmatter = yaml.safe_load(parts[1])
                    # 读取正文（具体指令）
                    body = parts[2].strip()
                    # 生产并添加工具
                    tools.append(
                        markdown_skill_factory(
                            name=frontmatter.get("name", skill_dir.name),
                            description=frontmatter.get("description", ""),
                            instructions=body
                        )
                    )
    return tools
