"""移动模块 —— 获取玩家状态。

实现 ``get_player_state`` 函数,从全局游戏上下文中取出指定玩家的状态字典,
作为移动 / 回血等模块操作玩家状态的统一入口。

``context`` 可以是完整游戏上下文(含 ``players`` 键的 ``dict``),也可以
直接是玩家容器(``list`` / ``tuple`` / 以 ``player_id`` 为键的 ``dict``):

    context = get_global_context()
    p1 = get_player_state(context, 0)   # 完整上下文 -> 自动取 context['players'][0]

返回的是实际存储的玩家状态 ``dict`` 的引用(原地修改会反映到上下文),
因此 ``apply_gravity`` / ``update_position`` / ``jump_logic`` 等可直接修改它。
"""


def get_player_state(context, player_id):
    """从上下文中取出指定玩家的状态。

    Args:
        context: 完整游戏上下文(含 ``players`` 键的 ``dict``),或直接为
            玩家容器(``dict`` 以 ``player_id`` 为键、``list`` / ``tuple``
            以 ``player_id`` 为下标)。
        player_id: 玩家标识,``dict`` 容器时作为键,序列容器时作为下标。

    Returns:
        对应玩家的状态 ``dict``;若上下文为空、玩家不存在或类型不支持,
        返回 ``None`` 供调用方判空。
    """
    # 防御:上下文为空时无法取状态。
    if not context:
        return None

    # 若传入的是完整游戏上下文(含 'players' 键),先取出玩家容器。
    if isinstance(context, dict) and 'players' in context:
        context = context['players']

    # 字典容器:按键取值,键不存在时返回 None。
    if isinstance(context, dict):
        return context.get(player_id)

    # 序列容器(仅 list / tuple):按下标取值,越界 / 非法下标返回 None。
    if isinstance(context, (list, tuple)):
        try:
            if player_id < 0:
                return None
            return context[player_id]
        except (TypeError, IndexError):
            return None

    # 其它类型(如 str 等)不支持作为上下文,返回 None。
    return None
