"""移动模块 —— 重力与垂直位移。

实现 ``apply_gravity`` 函数,负责角色的重力加速度、垂直位移与落地/顶边碰撞,
即「重力 + 位移一体」:

    - 未落地时,垂直速度 ``vy`` 每帧累加 ``gravity * dt``(向下为正),
      并用 ``TERMINAL_VELOCITY`` 钳位,防止无限加速。
    - 累加后按 ``vy`` 更新垂直位置 ``y``。
    - 脚底触及 ``ground_y`` 时落地:钳位到地面、清零 ``vy``、置 ``on_ground``。
    - (可选)提供 ``ceiling_y`` 时,上升触及天花板会被钳位并抵消向上速度。

职责边界(与同目录其它函数协同):
    - ``apply_gravity``:只处理垂直方向(重力 + 上下位移 + 落地)。
    - ``update_position``:负责水平位移与左右边界碰撞。
    - ``jump_logic``:在可起跳时设置 ``vy`` 为负的起跳初速并把 ``on_ground`` 置假。

坐标约定(与项目「极简线条地图」一致):
    - ``y`` 为角色脚底中心纵坐标,向下为正(pygame 默认坐标)。
    - ``ground_y`` 为地面线纵坐标,脚底停靠于此。
"""

# ---- 重力常量(极简线条风格,按需调整) ----
DEFAULT_GRAVITY = 2000.0    # 重力加速度(像素 / 秒^2),向下为正
TERMINAL_VELOCITY = 1500.0  # 最大下落速度(像素 / 秒),防止无限加速


def apply_gravity(player_state, dt):
    """对角色施加重力、更新垂直位置,并处理落地/顶边碰撞。

    Args:
        player_state: 单个玩家的状态 ``dict``,需包含以下键:
            - ``y``: 当前垂直位置(脚底,向下为正)。
            - ``vy``: 当前垂直速度(向下为正)。
            - ``on_ground``: 是否落地(布尔)。
            - ``ground_y``: 地面线纵坐标,脚底停靠于此。
            - (可选)``gravity``: 重力加速度,缺失时使用 DEFAULT_GRAVITY。
            - (可选)``ceiling_y``: 天花板纵坐标,缺失时不做顶边限制。
        dt: 本帧耗时(秒),由游戏循环传入,保证与帧率无关。

    Returns:
        None,直接原地修改 ``player_state``,不返回任何值。
    """
    # 防御:状态为空(未初始化或传入 None)时不做任何处理,避免崩溃。
    if not player_state:
        return

    gravity = player_state.get("gravity", DEFAULT_GRAVITY)
    on_ground = player_state.get("on_ground", False)
    vy = player_state.get("vy", 0.0)
    y = player_state.get("y", 0.0)
    ground_y = player_state.get("ground_y")
    ceiling_y = player_state.get("ceiling_y")

    # 1) 未落地时受重力加速,并做终端速度钳位。
    if not on_ground:
        vy += gravity * dt
        if vy > TERMINAL_VELOCITY:
            vy = TERMINAL_VELOCITY

    # 2) 按垂直速度更新位置。
    y += vy * dt

    # 3) 落地碰撞:脚底触及地面线时钳位、清零速度、标记落地。
    if ground_y is not None and y >= ground_y:
        y = ground_y
        vy = 0.0
        on_ground = True
    else:
        # 3b) 顶边碰撞(可选):上升触及天花板时钳位并抵消向上速度。
        if ceiling_y is not None and y < ceiling_y:
            y = ceiling_y
            vy = 0.0
        on_ground = False

    player_state["y"] = y
    player_state["vy"] = vy
    player_state["on_ground"] = on_ground
