"""示例插件 - 演示如何创建新插件"""
from marku.core.plugins import hookimpl


@hookimpl
def run(config: dict) -> dict:
    """示例插件实现

    这是一个简单的示例插件，演示插件的基本结构。
    实际的插件应该实现具体的业务逻辑。
    """
    input_path = config.get("input", "")
    dry_run = config.get("dry_run", False)

    # 这里实现具体的处理逻辑
    # 例如：读取文件、处理内容、生成diff等

    if dry_run:
        return {
            "ok": True,
            "changed": False,
            "diff": "示例插件 dry-run 模式",
            "details": ["插件执行成功", f"输入路径: {input_path}"]
        }
    else:
        # 实际处理逻辑
        return {
            "ok": True,
            "changed": True,
            "diff": "示例插件处理完成",
            "details": ["文件已处理", f"输入路径: {input_path}"]
        }


# 如果需要插件有自己的配置，可以定义插件配置类
class ExamplePluginConfig:
    """插件配置类"""
    def __init__(self):
        self.enabled = True
        self.max_files = 100
        self.output_format = "markdown"

    @classmethod
    def from_dict(cls, config: dict) -> 'ExamplePluginConfig':
        """从配置字典创建配置对象"""
        instance = cls()
        instance.enabled = config.get("enabled", True)
        instance.max_files = config.get("max_files", 100)
        instance.output_format = config.get("output_format", "markdown")
        return instance
