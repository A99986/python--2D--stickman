"""移动模块 —— 跳跃逻辑。

实现 ``jump_logic`` 函数,在玩家可起跳时(落地且收到起跳指令)设置
向上的初速度,交给 ``apply_gravity`` 完成后续的上升 / 下落 / 落地。

职责边界(与同目录其它函数协同):
    - ``jump_logic``:只负责「起跳」——设置 ``vy`` 为负的起跳初速并把
      ``on_ground`` 置假。
    - ``apply_gravity``:处理重力加速与垂直位移、落地。
    - ``update_position``:处理水平位移与左右边界。

起跳条件:
    - ``on_ground`` 为真(只有落地才能起跳,禁止二段跳)。
    - ``jump_pressed`` 为真(由游戏循环在检测到起跳键按下时传入)。

坐标/速度约定(与 ``apply_gravity`` 一致):
    - ``vy`` 向下为正,起跳为负值(向上)。
"""

# ---- 跳跃常量(极简线条风格,按需调整) ----
DEFAULT_JUMP_SPEED = 800.0  # 起跳初速(像素 / 秒),正值,内部取负表示向上


def jump_logic(player_state, jump_pressed):
    """若可起跳则设置向上的初速度。

    Args:
        player_state: 单个玩家的状态 ``dict``,需包含以下键:
            - ``vy``: 垂直速度(向下为正),起跳时被设为负的起跳初速。
            - ``on_ground``: 是否落地(布尔),起跳后置假。
            - (可选)``jump_speed``: 起跳初速(正值),缺失时使用 DEFAULT_JUMP_SPEED。
        jump_pressed: 本帧是否收到起跳指令(布尔),由游戏循环传入。

    Returns:
        None,直接原地修改 ``player_state``,不返回任何值。
    """
    # 防御:状态为空(未初始化或传入 None)时不做任何处理,避免崩溃。
    if not player_state:
        return

    # 未收到起跳指令则不跳。
    if not jump_pressed:
        return

    # 未落地时不跳,禁止空中二段跳。
    if not player_state.get("on_ground", False):
        return

    jump_speed = player_state.get("jump_speed", DEFAULT_JUMP_SPEED)
    player_state["vy"] = -jump_speed
    player_state["on_ground"] = False
