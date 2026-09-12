"""移动模块 —— 悬浮平台碰撞(单向平台 / one-way platform)。

实现 ``resolve_platform_collision``,让悬浮块拥有碰撞体积:

    - 从上方下落、脚底越过平台顶面时落在平台上(``on_ground=True``),
      并记录所站平台 ``standing_platform``;站立期间跟随平台的垂直移动。
    - 从下方跳起可以直接穿过平台(单向),走出平台左右边缘会自然掉落。
    - 地面(``ground_y``)仍由 ``apply_gravity`` 负责,本模块只处理平台。

需要在垂直积分(``apply_gravity``)之前把积分前的脚底高度写入
``player_state['y_prev']``,供本模块做"本帧是否越过顶面"的判定。
"""

# 脚底中心相对平台边缘的水平容差(像素),让边缘落脚更顺滑。
DEFAULT_EDGE_PAD = 6.0


def _find_platform(platforms, index):
    """按平台 index 找到当前帧对应的平台几何。"""
    for platform in platforms:
        if platform.get("index") == index:
            return platform
    return None


def _horizontal_overlap(x, rect, pad=DEFAULT_EDGE_PAD):
    """玩家脚底中心 x 是否落在平台横向区间(含容差)内。"""
    return (rect.left - pad) <= x <= (rect.right + pad)


def _land(player_state, platform):
    """把玩家放置到平台顶面并标记站立。"""
    player_state["y"] = float(platform["rect"].top)
    player_state["vy"] = 0.0
    player_state["on_ground"] = True
    player_state["standing_platform"] = platform["index"]


def resolve_platform_collision(player_state, platforms, edge_pad=DEFAULT_EDGE_PAD):
    """处理一帧内玩家与悬浮平台的碰撞。

    Args:
        player_state: 单个玩家状态 dict,需含 ``x`` / ``y`` / ``vy`` /
            ``on_ground`` / ``y_prev`` / ``standing_platform``。
        platforms: 当前帧平台几何列表(由 ``map.get_platforms`` 提供),
            每个元素含 ``index`` 与 ``rect``。
        edge_pad: 水平落脚容差。

    Returns:
        None,直接原地修改 ``player_state``。
    """
    if not player_state or not platforms:
        return

    standing = player_state.get("standing_platform")

    # 1) 已站在某平台上:水平仍处于平台范围内就继续站立(垂直跟随平台),
    #    走出左右边缘则清除站立标记,随后进入下落流程。
    if standing is not None:
        platform = _find_platform(platforms, standing)
        if platform is not None and _horizontal_overlap(
            player_state.get("x", 0.0), platform["rect"], edge_pad
        ):
            _land(player_state, platform)
            return
        player_state["standing_platform"] = None

    # 2) 空中:上升中不落脚(允许从下方穿过);下落且本帧越过某平台顶面时落脚。
    if player_state.get("vy", 0.0) < 0:
        return

    y_prev = player_state.get("y_prev")
    if y_prev is None:
        return
    y_now = player_state.get("y", y_prev)
    x = player_state.get("x", 0.0)

    for platform in platforms:
        rect = platform["rect"]
        top = rect.top
        if y_prev <= top <= y_now and _horizontal_overlap(x, rect, edge_pad):
            _land(player_state, platform)
            return
