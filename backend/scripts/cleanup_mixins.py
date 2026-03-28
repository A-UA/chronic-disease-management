import os
import re

def replace_uuid_mixin(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'UUIDMixin' in content:
                    # Replace in imports and class definitions
                    new_content = re.sub(r'\bUUIDMixin\b', 'IDMixin', content)
                    
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {path}")

if __name__ == "__main__":
    target = 'app/db/models' if os.path.exists('app/db/models') else 'backend/app/db/models'
    replace_uuid_mixin(target)
