"""移动模块 —— 水平位移与边界碰撞。

实现 ``update_position`` 函数,负责角色的水平位移与左右边界碰撞,
与 ``apply_gravity``(垂直方向)配合,共同完成角色的空间移动。

职责边界(与同目录其它函数协同):
    - ``apply_gravity``:处理垂直方向(重力 + 上下位移 + 落地)。
    - ``update_position``:处理水平位移 + 左右边界钳位。
    - ``jump_logic``:处理起跳初速。

水平位移规则:
    - ``x += vx * dt``,``vx`` 由游戏循环根据输入设置(正值向右、负值向左)。
    - 钳位到 ``[min_x, max_x]``,防止角色移出屏幕边界。

坐标约定:
    - ``x`` 为角色参考点的横坐标(通常为中心),与 ``min_x`` / ``max_x``
      使用同一参考点,由调用方保证一致。
"""

# ---- 边界常量(极简线条风格,按需调整) ----
DEFAULT_MIN_X = 0.0      # 默认左边界
DEFAULT_MAX_X = 1280.0   # 默认右边界(按屏幕宽度调整)


def update_position(player_state, dt):
    """按水平速度更新位置,并做左右边界钳位。

    Args:
        player_state: 单个玩家的状态 ``dict``,需包含以下键:
            - ``x``: 当前水平位置。
            - ``vx``: 当前水平速度(正值向右、负值向左)。
            - (可选)``min_x``: 左边界,缺失时使用 DEFAULT_MIN_X。
            - (可选)``max_x``: 右边界,缺失时使用 DEFAULT_MAX_X。
        dt: 本帧耗时(秒),由游戏循环传入,保证与帧率无关。

    Returns:
        None,直接原地修改 ``player_state``,不返回任何值。
    """
    # 防御:状态为空(未初始化或传入 None)时不做任何处理,避免崩溃。
    if not player_state:
        return

    x = player_state.get("x", 0.0)
    vx = player_state.get("vx", 0.0)
    min_x = player_state.get("min_x", DEFAULT_MIN_X)
    max_x = player_state.get("max_x", DEFAULT_MAX_X)

    # 水平位移。
    x += vx * dt

    # 边界钳位:若边界被误配为 min_x > max_x,先交换以保证区间有效。
    if min_x > max_x:
        min_x, max_x = max_x, min_x
    x = max(min_x, min(x, max_x))

    player_state["x"] = x
