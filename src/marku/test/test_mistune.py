import json
from os import path
import mistune

file = open("1.md", "r", encoding="utf-8")
text = file.read()
markdown = mistune.create_markdown(renderer='ast')
# markdown(text)
content = markdown(text)
json_str = json.dumps(content, ensure_ascii=False, indent=2)
output_file = path.join(path.dirname(__file__), "1.json")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(json_str)
# This file is part of the Marku project.   
