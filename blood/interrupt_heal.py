"""回血系统模块 —— 受击打断回血。

实现 ``interrupt_heal`` 函数,在玩家受到伤害时重置其回血倒计时,
使计时回血被打断:玩家需要重新等待完整的回血间隔后才能继续回血。

该函数是「生存模式可打断计时回血」闭环中的一环,配合
``update_heal_timer``(推进倒计时)与 ``update_hp``(回血/掉血)共同工作:

    - 正常流程:``heal_timer`` 从 ``heal_interval`` 开始逐帧递减,
      减到 0 后触发一次回血并重置。
    - 受击流程:``update_hp`` 收到负增量(掉血)时会调用 ``interrupt_heal``,
      把 ``heal_timer`` 直接拉回 ``heal_interval``,使回血进度归零。
"""


def interrupt_heal(player_state):
    """受击时打断回血,重置回血倒计时。

    Args:
        player_state: 单个玩家的状态 ``dict``,需包含以下键:
            - ``heal_timer``: 当前回血倒计时(秒),随时间递减。
            - ``heal_interval``: 满回血间隔(秒),即受击后需等待多久才能再次回血;
              缺失或 <= 0 时表示未开启回血,本函数不做任何处理。

    Returns:
        None,直接原地修改传入的 ``player_state``,不返回任何值。
    """
    # 防御:状态为空(未初始化或传入 None)时不做任何处理,避免崩溃。
    if not player_state:
        return

    interval = player_state.get("heal_interval", 0)
    # 未开启回血(快速模式:缺少 heal_interval 或间隔为 0)时无需打断,直接返回。
    if interval <= 0:
        return

    # 无条件重置:每次受击都打断回血进度,回血倒计时重新回到满冷却。
    # 即使当前倒计时已低于满值,也一并拉回,符合「受击打断」的语义。
    player_state["heal_timer"] = interval
