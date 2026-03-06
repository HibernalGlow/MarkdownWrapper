"""失效图片清理模块"""
from __future__ import annotations

import re
import urllib.parse
import os
from pathlib import Path
from typing import Dict, Any
from .base import BaseModule, ModuleContext
from .plugins import hookimpl


class MissingImageModule(BaseModule):
    name = "missing_image_remover"

    def is_image_valid(self, image_path: str, base_dir: str, check_file_uri: bool = True, check_relative: bool = False) -> bool:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            return True
        
        if image_path.startswith("data:"):
            return True
        
        # 解析文件 URI
        if image_path.startswith("file:///"):
            if not check_file_uri:
                return True
            path_str = image_path[8:]
            path_str = urllib.parse.unquote(path_str)
            if os.name == 'nt' and '/' in path_str:
                path_str = path_str.replace('/', '\\')
            return os.path.exists(path_str)
        
        # 解析其他相对路径或绝对路径
        if check_relative:
            path_str = urllib.parse.unquote(image_path)
            if os.path.isabs(path_str):
                return os.path.exists(path_str)
            full_path = os.path.join(base_dir, path_str)
            return os.path.exists(full_path)
            
        return True

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        check_file_uri = config.get("check_file_uri", True)
        check_relative = config.get("check_relative", False)
        
        pattern = re.compile(r'!\[(.*?)\]\(([^)]+)\)')
        changed = 0
        total = 0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        verbose = config.get("verbose", True)
        details: list = []
        
        for file in self._iter_markdown_files(input_path, config):
            total += 1
            text = file.read_text(encoding="utf-8")
            base_dir = str(file.parent)
            
            removed_count = 0
            
            def replacer(match):
                nonlocal removed_count
                image_path = match.group(2)
                
                if not self.is_image_valid(image_path, base_dir, check_file_uri, check_relative):
                    removed_count += 1
                    return ""  # 移除此图片
                
                return match.group(0)
                
            new_text = pattern.sub(replacer, text)
            modified = self._maybe_write(file, text, new_text, dry_run, diffs)
            
            if modified:
                changed += 1
                if verbose:
                    print(f"[missing_image_remover] CHANGED (Removed {removed_count} images) - {file}")
            elif verbose:
                print(f"[missing_image_remover] ok - {file}")
                
            details.append({"file": str(file), "changed": bool(modified), "removed_images": removed_count})
            
        print(f"[missing_image_remover] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}


# pluggy 插件入口
@hookimpl
def run(context: ModuleContext, config: Dict[str, Any]):
    mod = MissingImageModule()
    mod.run(context, config)
    return {"ok": True}
