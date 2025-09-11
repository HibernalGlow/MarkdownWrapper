"""插件系统 - 基于 pluggy 的成熟插件框架"""
from __future__ import annotations

import importlib.metadata
from typing import Dict, Any, Optional, List
from pluggy import PluginManager, HookimplMarker, HookspecMarker
import logging

# Hook 规范标记
hookspec = HookspecMarker("marku")
hookimpl = HookimplMarker("marku")

# 日志
logger = logging.getLogger(__name__)
_initialized = False


class MarkuSpec:
    """Marku 插件规范"""

    @hookspec
    def run(self, context, config: Dict[str, Any]) -> Dict[str, Any]:
        """插件执行入口

        Args:
            config: 插件配置字典

        Returns:
            结果字典，包含：
            - ok: bool - 是否执行成功
            - changed: bool - 是否有文件变更
            - diff: str - 变更详情
            - details: List[str] - 详细日志
            - error: str - 错误信息（如果有）
        """


class PluginRegistry:
    """插件注册表管理器"""

    def __init__(self):
        self._pm = PluginManager("marku")
        self._pm.add_hookspecs(MarkuSpec)
        self._legacy_registry = {}
        self._discovered_plugins = {}
        self._origins = {}  # name -> entry_point|builtin|legacy
        self._disabled = set()

    def register_legacy_module(self, name: str, module_class: Any):
        """注册遗留模块（向后兼容）"""
        # 若已注册同名插件则忽略
        try:
            if self._pm.has_plugin(name):
                return
        except Exception:
            pass
        self._legacy_registry[name] = module_class
        logger.debug(f"注册遗留模块: {name}")

    def discover_plugins(self):
        """自动发现插件"""
        # 1. 通过 pluggy 的入口加载（若可用）或手动 entry_points 发现
        try:
            load_ep = getattr(self._pm, "load_setuptools_entrypoints", None)
            if callable(load_ep):
                before = set(getattr(self._pm, "_name2plugin", {}).keys())
                load_ep("marku.plugins")
                after = set(getattr(self._pm, "_name2plugin", {}).keys())
                for name in sorted(after - before):
                    try:
                        plugin = self._pm.get_plugin(name)
                        self._discovered_plugins[name] = plugin
                        self._origins[name] = "entry_point"
                        logger.info(f"发现插件: {name} (entry_point)")
                    except Exception:
                        pass
            else:
                try:
                    for entry_point in importlib.metadata.entry_points(group="marku.plugins"):
                        try:
                            plugin = entry_point.load()
                            if not self._pm.has_plugin(entry_point.name):
                                self._pm.register(plugin, name=entry_point.name)
                                self._discovered_plugins[entry_point.name] = plugin
                                self._origins[entry_point.name] = "entry_point"
                                logger.info(f"发现插件: {entry_point.name} ({entry_point.module})")
                        except Exception as e:
                            logger.warning(f"加载插件失败 {entry_point.name}: {e}")
                except Exception as e:
                    logger.debug(f"没有找到 entry_points 插件: {e}")
        except Exception:
            # 安静失败，继续走后续注册
            pass

        # 2. 注册遗留模块作为插件
        try:
            for name, module_class in self._legacy_registry.items():
                try:
                    if not self._pm.has_plugin(name):
                        wrapper = LegacyModuleWrapper(module_class)
                        self._pm.register(wrapper, name=name)
                        self._discovered_plugins[name] = wrapper
                        self._origins[name] = "legacy"
                        logger.debug(f"注册遗留模块包装器: {name}")
                except Exception as e:
                    logger.debug(f"注册遗留模块失败 {name}: {e}")
        except Exception:
            pass

    def get_plugin(self, name: str) -> Optional[Any]:
        """获取插件"""
        return self._pm.get_plugin(name)

    def list_plugins(self) -> List[str]:
        """列出所有可用插件"""
        names = set(self._discovered_plugins.keys()) | set(self._legacy_registry.keys())
        # pluggy may keep an internal name->plugin mapping, try to use it
        try:
            nm = getattr(self._pm, "_name2plugin", None)
            if isinstance(nm, dict):
                names |= set(nm.keys())
        except Exception:
            pass
        return sorted(names)

    def list_plugins_status(self) -> List[Dict[str, Any]]:
        """列出插件的状态与来源"""
        items = []
        for n in self.list_plugins():
            items.append({
                "name": n,
                "enabled": self.has_plugin(n),
                "origin": self._origins.get(n, "unknown"),
            })
        return items

    def call_plugin(self, name: str, context, config: Dict[str, Any]) -> Dict[str, Any]:
        """调用插件"""
        plugin = self.get_plugin(name)
        if not plugin:
            raise ValueError(f"插件不存在: {name}")

        try:
            # 直接调用目标插件的 run（避免广播到所有插件）
            run_fn = getattr(plugin, "run", None)
            if callable(run_fn):
                return run_fn(context, config)
            return {"ok": False, "error": "插件未实现 run"}
        except Exception as e:
            logger.error(f"插件执行失败 {name}: {e}")
            return {"ok": False, "error": str(e)}

    def has_plugin(self, name: str) -> bool:
        """检查插件是否存在"""
        return self._pm.has_plugin(name)

    def is_disabled(self, name: str) -> bool:
        return name in self._disabled

    def disable(self, name: str) -> bool:
        """禁用插件: 从 pluggy 注销并记录禁用集"""
        try:
            if self._pm.has_plugin(name):
                self._pm.unregister(name=name)
            self._disabled.add(name)
            return True
        except Exception:
            return False

    def enable(self, name: str) -> bool:
        """启用插件: 从保存源重新注册"""
        try:
            if self._pm.has_plugin(name):
                # 已启用
                if name in self._disabled:
                    self._disabled.discard(name)
                return True
            plugin = self._discovered_plugins.get(name)
            if plugin is None and name in self._legacy_registry:
                plugin = LegacyModuleWrapper(self._legacy_registry[name])
            if plugin is None:
                return False
            self._pm.register(plugin, name=name)
            self._disabled.discard(name)
            return True
        except Exception:
            return False

    def get_origin(self, name: str) -> str:
        return self._origins.get(name, "unknown")


class LegacyModuleWrapper:
    """遗留模块包装器 - 将旧模块适配为新插件接口"""

    def __init__(self, module_class: Any):
        self.module_class = module_class

    @hookimpl
    def run(self, context, config: Dict[str, Any]) -> Dict[str, Any]:
        """包装遗留模块的 run 方法"""
        try:
            # 创建模块实例
            instance = self.module_class()

            # 调用遗留的 run 方法
            result = instance.run(context, config)

            # 标准化返回格式
            if isinstance(result, dict):
                return result
            else:
                # 如果返回的不是字典，包装一下
                return {
                    "ok": True,
                    "changed": True,
                    "result": result,
                    "details": [f"执行完成: {result}"]
                }

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "details": [f"执行失败: {e}"]
            }


# 全局插件注册表实例
plugin_registry = PluginRegistry()


def create(name: str) -> Any:
    """创建插件实例（向后兼容接口）"""
    plugin = plugin_registry.get_plugin(name)
    if not plugin:
        raise KeyError(f"插件不存在: {name}")
    return plugin


def initialize_plugins():
    """初始化插件系统"""
    global _initialized
    if _initialized:
        return
    # 注册遗留模块（从旧的 registry 导入）
    try:
        from .registry import REGISTRY as legacy_registry
        for name, module_class in legacy_registry.items():
            plugin_registry.register_legacy_module(name, module_class)
    except ImportError:
        logger.debug("未找到遗留注册表，跳过导入")

    # 发现插件
    plugin_registry.discover_plugins()

    # 内置插件模块注册（无需打包也可作为插件使用）
    try:
        import importlib as _il
        builtin_modules = {
            "consecutive_header": ".consecutive_header",
            "content_dedup": ".content_dedup",
            "html2sy_table": ".html_table",
            "image_path_replacer": ".image_path",
            "single_orderlist_remover": ".single_orderlist",
            "t2list": ".t2list_module",
            "content_replace": ".content_replace",
            "title_convert": ".title_convert",
        }
        for _name, _rel in builtin_modules.items():
            try:
                if not plugin_registry._pm.has_plugin(_name):
                    mod = _il.import_module(_rel, __package__)
                    if hasattr(mod, "run"):
                        plugin_registry._pm.register(mod, name=_name)
                        plugin_registry._discovered_plugins[_name] = mod
                        plugin_registry._origins[_name] = "builtin"
            except Exception:
                continue
    except Exception:
        pass

    _initialized = True
    logger.info(f"插件系统初始化完成，发现 {len(plugin_registry.list_plugins())} 个插件")


# 为了向后兼容，保留原有的 REGISTRY 接口
REGISTRY = plugin_registry

__all__ = ["plugin_registry", "create", "initialize_plugins", "REGISTRY", "MarkuSpec", "hookimpl"]
