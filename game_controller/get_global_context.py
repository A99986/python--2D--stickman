"""游戏控制模块 —— 全局上下文访问。

维护一个模块级的全局游戏上下文,提供 ``get_global_context`` 与
``set_global_context`` 两个访问接口。整个游戏的共享状态(玩家、模式、
计分、回合等)都通过它读写,避免各函数间层层传参。

    - ``init_game_context`` 初始化后调用 ``set_global_context`` 保存。
    - 移动 / 回血 / 渲染等模块需要时通过 ``get_global_context`` 获取。
"""

_global_context = None


def get_global_context():
    """返回全局游戏上下文。

    Returns:
        当前全局上下文(通常为 ``dict``);尚未初始化时为 ``None``。
    """
    return _global_context


def set_global_context(context):
    """设置全局游戏上下文。

    Args:
        context: 待保存的全局上下文(通常由 ``init_game_context`` 传入)。

    Returns:
        None。
    """
    global _global_context
    _global_context = context
