import os
import re

entity_dir = r"d:\codes\chronic-disease-management\backend-java\cdm-auth\src\main\java\com\cdm\auth\entity"
vo_dir = r"d:\codes\chronic-disease-management\backend-java\cdm-auth\src\main\java\com\cdm\auth\vo"

for filename in os.listdir(entity_dir):
    if not filename.endswith("Entity.java"): continue
    filepath = os.path.join(entity_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Imports
    content = re.sub(r'import jakarta\.persistence\.\*;\n', 'import com.baomidou.mybatisplus.annotation.TableName;\nimport com.baomidou.mybatisplus.annotation.TableField;\nimport com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;\n', content)
    
    # Class annotations
    content = re.sub(r'@Entity\s*\n@Table\(name\s*=\s*"([^"]+)"\)', r'@TableName(value = "\1", autoResultMap = true)', content)
    
    # @Column, @JdbcTypeCode
    content = re.sub(r'@Column(\([^)]*\))?\s*\n', '', content)
    content = re.sub(r'@JdbcTypeCode\([^)]*\)\s*\n', '', content)
    
    # JSON field
    content = re.sub(r'private Map<String, Object> meta;', r'@TableField(typeHandler = JacksonTypeHandler.class)\n    private Map<String, Object> meta;', content)
    
    # toVo method Strings to Long
    content = re.sub(r'\.parentId\(entity\.getParentId\(\) != null \? String\.valueOf\(entity\.getParentId\(\)\) : null\)', r'.parentId(entity.getParentId())', content)
    content = re.sub(r'\.tenantId\(entity\.getTenantId\(\) != null \? String\.valueOf\(entity\.getTenantId\(\)\) : null\)', r'.tenantId(entity.getTenantId())', content)
    
    # Relation annotations
    content = re.sub(r'@ManyToMany\s*\n', '', content)
    content = re.sub(r'@JoinTable\([^)]+\)\s*\n', '@TableField(exist = false)\n', content)

    # Change id types in entity
    content = re.sub(r'private String parentId;', 'private Long parentId;', content)
    content = re.sub(r'private String tenantId;', 'private Long tenantId;', content)
    content = re.sub(r'private String orgId;', 'private Long orgId;', content)
    content = re.sub(r'private String userId;', 'private Long userId;', content)
    content = re.sub(r'private String roleId;', 'private Long roleId;', content)
    content = re.sub(r'private String parentRoleId;', 'private Long parentRoleId;', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Update VOs
for filename in os.listdir(vo_dir):
    if not filename.endswith("Vo.java"): continue
    filepath = os.path.join(vo_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(r'private String id;', 'private Long id;', content)
    content = re.sub(r'private String parentId;', 'private Long parentId;', content)
    content = re.sub(r'private String tenantId;', 'private Long tenantId;', content)
    content = re.sub(r'private String orgId;', 'private Long orgId;', content)
    content = re.sub(r'private String userId;', 'private Long userId;', content)
    content = re.sub(r'private String roleId;', 'private Long roleId;', content)
    content = re.sub(r'private String parentRoleId;', 'private Long parentRoleId;', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Entities and VOs refactored.")
