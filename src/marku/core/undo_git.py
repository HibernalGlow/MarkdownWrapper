"""marku Git 撤销管理器

使用 Git 管理处理历史。
支持在非 Git 目录下自动 git init。
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from datetime import datetime
from git import Repo, InvalidGitRepositoryError, GitCommandError

logger = logging.getLogger(__name__)

class GitUndoManager:
    """marku Git 撤销管理器"""

    def __init__(self, root: Path):
        self.root = root
        self.repo = self._get_or_init_repo()

    def _get_or_init_repo(self) -> Repo:
        try:
            repo = Repo(self.root, search_parent_directories=True)
            # 确保我们在正确的根路径下工作，或者至少这是我们处理的子集
            return repo
        except InvalidGitRepositoryError:
            logger.info(f"初始化 Git 仓库于: {self.root}")
            repo = Repo.init(self.root)
            # 创建初始提交
            gitignore = self.root / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text("__pycache__/\n.marku/\n*.bak\n", encoding="utf-8")
            repo.index.add([".gitignore"])
            repo.index.commit("Initial commit (marku setup)")
            return repo

    def is_dirty(self) -> bool:
        """检查是否有未提交的变更"""
        return self.repo.is_dirty(untracked_files=True)

    def save_state(self, message: str) -> str | None:
        """提交当前变更
        
        Returns:
            hexsha or None if nothing changed
        """
        try:
            # 仅添加 .md 文件或者所有文件？
            # 为了安全，这里添加所有文件，除非用户有 .gitignore
            self.repo.git.add(A=True)
            if not self.repo.is_dirty(index=True):
                return None
            
            commit = self.repo.index.commit(f"[marku] {message}")
            logger.info(f"保存状态: {commit.hexsha} - {message}")
            return commit.hexsha
        except GitCommandError as e:
            logger.error(f"Git 提交失败: {e}")
            return None

    def undo_latest(self) -> bool:
        """通过 checkout 上一个版本来撤销"""
        try:
            # 寻找最近的一个 [marku] 提交
            commits = list(self.repo.iter_commits(max_count=20))
            last_marku_commit = None
            for i, commit in enumerate(commits):
                if commit.message.startswith("[marku]"):
                    # 如果这是最新的提交，我们需要的是它之前的那个状态
                    # 或者如果是 pre-run，我们想回到它之前
                    last_marku_commit = commit
                    break
            
            if not last_marku_commit:
                print("[yellow]未发现可撤销的 marku 操作记录[/yellow]")
                return False

            # 撤销逻辑：
            # 实际上我们想恢复到该 commit 之前的那个状态
            # 使用 git checkout <commit>^ -- .
            self.repo.git.checkout("HEAD^", "--", ".")
            # 撤销后需要提交一下这个“撤销”动作吗？或者让用户决定？
            # 通常 marku 应该自动提交撤销
            self.save_state(f"Undo operation: {last_marku_commit.summary}")
            return True
        except Exception as e:
            logger.error(f"撤销失败: {e}")
            print(f"[red]撤销失败: {e}[/red]")
            return False

    def get_history(self, limit: int = 10) -> list[dict]:
        history = []
        try:
            for commit in self.repo.iter_commits(max_count=limit * 2):
                if commit.message.startswith("[marku]"):
                    history.append({
                        "id": commit.hexsha[:8],
                        "summary": commit.summary.replace("[marku] ", ""),
                        "time": datetime.fromtimestamp(commit.authored_date),
                        "author": commit.author.name
                    })
                if len(history) >= limit:
                    break
        except Exception:
            pass
        return history

    def revert_to(self, hexsha: str) -> bool:
        """回滚到指定的提交"""
        try:
            # 检出指定提交的文件到当前工作区
            self.repo.git.checkout(hexsha, "--", ".")
            self.save_state(f"Revert to {hexsha[:8]}")
            return True
        except GitCommandError as e:
            print(f"[red]回滚失败: {e}[/red]")
            return False
