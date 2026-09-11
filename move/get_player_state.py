"""移动模块 —— 获取玩家状态。

实现 ``get_player_state`` 函数,从全局游戏上下文中取出指定玩家的状态字典,
作为移动 / 回血等模块操作玩家状态的统一入口。

配合 ``game_controller.get_global_context`` 使用:

    context = get_global_context()
    p1 = get_player_state(context, 0)
    apply_gravity(p1, dt)

返回的是上下文中实际存储的玩家状态 ``dict`` 的引用(原地修改会反映到上下文),
因此 ``apply_gravity`` / ``update_position`` / ``jump_logic`` 等可直接修改它。
"""


def get_player_state(context, player_id):
    """从上下文中取出指定玩家的状态。

    Args:
        context: 全局游戏上下文,``dict``(以 ``player_id`` 为键)或
            ``list`` / ``tuple``(以 ``player_id`` 为下标)。
        player_id: 玩家标识,``dict`` 上下文时作为键,序列上下文时作为下标。

    Returns:
        对应玩家的状态 ``dict``;若上下文为空、玩家不存在或类型不支持,
        返回 ``None`` 供调用方判空。
    """
    # 防御:上下文为空时无法取状态。
    if not context:
        return None

    # 字典上下文:按键取值,键不存在时返回 None。
    if isinstance(context, dict):
        return context.get(player_id)

    # 序列上下文(仅 list / tuple):按下标取值,越界 / 非法下标返回 None。
    if isinstance(context, (list, tuple)):
        try:
            if player_id < 0:
                return None
            return context[player_id]
        except (TypeError, IndexError):
            return None

    # 其它类型(如 str 等)不支持作为上下文,返回 None。
    return None
