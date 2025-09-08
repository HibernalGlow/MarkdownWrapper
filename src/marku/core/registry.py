"""模块注册表"""
from __future__ import annotations

from typing import Dict, Type
from .base import BaseModule
from .consecutive_header import ConsecutiveHeaderModule
from .content_dedup import ContentDedupModule
from .html_table import HtmlTableModule
from .image_path import ImagePathModule
from .single_orderlist import SingleOrderListModule
from .t2list_module import T2ListModule
from .content_replace import ContentReplaceModule
from .title_convert import TitleNormalizeModule


REGISTRY: Dict[str, Type[BaseModule]] = {
    cls.name: cls for cls in [
        ConsecutiveHeaderModule,
        ContentDedupModule,
        HtmlTableModule,
        ImagePathModule,
        SingleOrderListModule,
        T2ListModule,
    ContentReplaceModule,
    TitleNormalizeModule,
    ]
}

def create(name: str) -> BaseModule:
    if name not in REGISTRY:
        raise KeyError(f"未注册模块: {name}")
    return REGISTRY[name]()

__all__ = ["create", "REGISTRY"]
