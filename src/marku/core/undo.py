"""marku 撤销管理器

使用 SQLite 持久化存储操作历史，支持撤销文件修改。
参考 trename 的撤销系统设计。
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = Path.home() / ".marku" / "undo.db"


@dataclass
class FileOperation:
    """单次文件操作"""
    file_path: Path
    backup_path: Path  # 备份文件路径
    module_name: str   # 执行的模块名


@dataclass
class UndoRecord:
    """撤销记录"""
    id: str
    timestamp: datetime
    module_name: str
    description: str
    operations: list[FileOperation]
    undone: bool = False


@dataclass
class UndoResult:
    """撤销操作结果"""
    success_count: int
    failed_count: int
    failed_items: list[tuple[Path, str]]  # (file_path, error_msg)


class UndoManager:
    """marku 撤销管理器 - 使用 SQLite 存储撤销记录"""

    def __init__(self, db_path: Path | None = None):
        """初始化撤销管理器

        Args:
            db_path: 数据库文件路径，默认为 ~/.marku/undo.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._backup_dir = self.db_path.parent / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """创建数据库表"""
        cursor = self.conn.cursor()

        # 批次表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_batches (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                module_name TEXT NOT NULL,
                description TEXT,
                undone INTEGER DEFAULT 0
            )
        """)

        # 操作表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                seq_order INTEGER NOT NULL,
                FOREIGN KEY (batch_id) REFERENCES undo_batches(id)
            )
        """)

        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_operations_batch 
            ON undo_operations(batch_id)
        """)

        self.conn.commit()

    def backup_file(self, file_path: Path, batch_id: str) -> Path:
        """备份单个文件

        Args:
            file_path: 要备份的文件路径
            batch_id: 批次 ID

        Returns:
            备份文件路径
        """
        batch_backup_dir = self._backup_dir / batch_id
        batch_backup_dir.mkdir(parents=True, exist_ok=True)

        # 使用 UUID 确保唯一性（防止同名文件冲突）
        backup_name = f"{uuid.uuid4().hex[:8]}_{file_path.name}"
        backup_path = batch_backup_dir / backup_name

        shutil.copy2(str(file_path), str(backup_path))
        return backup_path

    def start_batch(self, module_name: str, description: str = "") -> str:
        """开始一个新的操作批次

        Args:
            module_name: 模块名称
            description: 操作描述

        Returns:
            批次 ID
        """
        batch_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO undo_batches (id, timestamp, module_name, description) VALUES (?, ?, ?, ?)",
            (batch_id, timestamp, module_name, description),
        )
        self.conn.commit()

        logger.info(f"开始批次 {batch_id}: {module_name}")
        return batch_id

    def record_operation(
        self, batch_id: str, file_path: Path, backup_path: Path, seq_order: int
    ) -> None:
        """记录单个文件操作

        Args:
            batch_id: 批次 ID
            file_path: 原文件路径
            backup_path: 备份文件路径
            seq_order: 操作顺序
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO undo_operations 
               (batch_id, file_path, backup_path, seq_order) 
               VALUES (?, ?, ?, ?)""",
            (batch_id, str(file_path), str(backup_path), seq_order),
        )
        self.conn.commit()

    def finish_batch(self, batch_id: str, operation_count: int) -> None:
        """完成批次（仅用于日志）"""
        logger.info(f"完成批次 {batch_id}: {operation_count} 个文件")

    def undo(self, batch_id: str) -> UndoResult:
        """撤销指定批次的操作

        Args:
            batch_id: 批次 ID

        Returns:
            撤销结果
        """
        cursor = self.conn.cursor()

        # 检查批次是否存在且未撤销
        cursor.execute(
            "SELECT undone FROM undo_batches WHERE id = ?", (batch_id,)
        )
        row = cursor.fetchone()

        if not row:
            return UndoResult(
                success_count=0,
                failed_count=0,
                failed_items=[(Path(), f"批次不存在: {batch_id}")],
            )

        if row[0]:
            return UndoResult(
                success_count=0,
                failed_count=0,
                failed_items=[(Path(), f"批次已撤销: {batch_id}")],
            )

        # 获取操作记录
        cursor.execute(
            """SELECT file_path, backup_path FROM undo_operations 
               WHERE batch_id = ? ORDER BY seq_order""",
            (batch_id,),
        )
        operations = cursor.fetchall()

        success_count = 0
        failed_count = 0
        failed_items: list[tuple[Path, str]] = []

        # 执行撤销（从备份恢复）
        for file_path_str, backup_path_str in operations:
            file_path = Path(file_path_str)
            backup_path = Path(backup_path_str)

            try:
                if backup_path.exists():
                    shutil.copy2(str(backup_path), str(file_path))
                    success_count += 1
                    logger.info(f"恢复: {file_path.name}")
                else:
                    failed_count += 1
                    failed_items.append(
                        (file_path, f"备份不存在: {backup_path}")
                    )
            except Exception as e:
                failed_count += 1
                failed_items.append((file_path, str(e)))
                logger.error(f"恢复失败 {file_path}: {e}")

        # 标记批次为已撤销
        cursor.execute(
            "UPDATE undo_batches SET undone = 1 WHERE id = ?", (batch_id,)
        )
        self.conn.commit()

        # 清理备份目录
        batch_backup_dir = self._backup_dir / batch_id
        if batch_backup_dir.exists():
            shutil.rmtree(str(batch_backup_dir), ignore_errors=True)

        return UndoResult(
            success_count=success_count,
            failed_count=failed_count,
            failed_items=failed_items,
        )

    def undo_latest(self) -> UndoResult:
        """撤销最近一次操作

        Returns:
            撤销结果
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id FROM undo_batches 
               WHERE undone = 0 
               ORDER BY timestamp DESC LIMIT 1"""
        )
        row = cursor.fetchone()

        if not row:
            return UndoResult(
                success_count=0,
                failed_count=0,
                failed_items=[(Path(), "没有可撤销的操作")],
            )

        return self.undo(row[0])

    def get_history(self, limit: int = 10) -> list[UndoRecord]:
        """获取最近的操作历史

        Args:
            limit: 返回记录数量限制

        Returns:
            撤销记录列表
        """
        cursor = self.conn.cursor()

        # 获取批次
        cursor.execute(
            """SELECT id, timestamp, module_name, description, undone FROM undo_batches 
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        batches = cursor.fetchall()

        records: list[UndoRecord] = []

        for batch_id, timestamp_str, module_name, description, undone in batches:
            # 获取该批次的操作
            cursor.execute(
                """SELECT file_path, backup_path FROM undo_operations 
                   WHERE batch_id = ? ORDER BY seq_order""",
                (batch_id,),
            )
            ops = [
                FileOperation(
                    file_path=Path(fp),
                    backup_path=Path(bp),
                    module_name=module_name,
                )
                for fp, bp in cursor.fetchall()
            ]

            records.append(
                UndoRecord(
                    id=batch_id,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    module_name=module_name,
                    operations=ops,
                    description=description or "",
                    undone=bool(undone),
                )
            )

        return records

    def clear_history(self, keep_recent: int = 0) -> int:
        """清理历史记录和备份

        Args:
            keep_recent: 保留最近的记录数量

        Returns:
            删除的记录数量
        """
        cursor = self.conn.cursor()

        # 获取要删除的批次 ID（用于清理备份）
        if keep_recent > 0:
            cursor.execute(
                """SELECT id FROM undo_batches 
                   ORDER BY timestamp DESC LIMIT -1 OFFSET ?""",
                (keep_recent,),
            )
        else:
            cursor.execute("SELECT id FROM undo_batches")

        to_delete = [row[0] for row in cursor.fetchall()]

        # 清理备份目录
        for batch_id in to_delete:
            batch_backup_dir = self._backup_dir / batch_id
            if batch_backup_dir.exists():
                shutil.rmtree(str(batch_backup_dir), ignore_errors=True)

        # 删除数据库记录
        if keep_recent > 0:
            cursor.execute(
                """SELECT id FROM undo_batches 
                   ORDER BY timestamp DESC LIMIT ?""",
                (keep_recent,),
            )
            keep_ids = [row[0] for row in cursor.fetchall()]

            if keep_ids:
                placeholders = ",".join("?" * len(keep_ids))
                cursor.execute(
                    f"DELETE FROM undo_operations WHERE batch_id NOT IN ({placeholders})",
                    keep_ids,
                )
                cursor.execute(
                    f"DELETE FROM undo_batches WHERE id NOT IN ({placeholders})",
                    keep_ids,
                )
        else:
            cursor.execute("DELETE FROM undo_operations")
            cursor.execute("DELETE FROM undo_batches")

        deleted = len(to_delete)
        self.conn.commit()
        return deleted

    def close(self) -> None:
        """关闭数据库连接"""
        self.conn.close()

    def __enter__(self) -> "UndoManager":
        return self

    def __exit__(self, *args) -> None:
        self.close()


# 全局单例（可选）
_undo_manager: UndoManager | None = None


def get_undo_manager() -> UndoManager:
    """获取全局撤销管理器单例"""
    global _undo_manager
    if _undo_manager is None:
        _undo_manager = UndoManager()
    return _undo_manager
