"""回血系统模块 —— 推进回血倒计时。

实现 ``update_heal_timer`` 函数,逐帧推进生存模式下的回血倒计时,
并在倒计时归零时触发一次回血、重置倒计时。

这是「计时回血」的核心推进逻辑,配合 ``interrupt_heal``(受击打断)
与 ``update_hp``(掉血/回血结算)共同构成完整回血闭环:

    - ``update_heal_timer`` 每帧被游戏循环调用,传入本帧耗时 ``dt``。
    - 快速模式(未开启回血,即 ``heal_interval`` 缺失或 <= 0)时直接返回。
    - 死亡(``hp <= 0``)或满血(``hp >= max_hp``)时不再推进;
      受击后由 ``interrupt_heal`` 重新计时。
"""


def update_heal_timer(player_state, dt):
    """推进回血倒计时,归零时回一次血。

    Args:
        player_state: 单个玩家的状态 ``dict``,需包含以下键:
            - ``hp``: 当前血量。
            - ``max_hp``: 最大血量。
            - ``heal_timer``: 当前回血倒计时(秒),随时间递减。
            - ``heal_interval``: 满回血间隔(秒),缺失或 <= 0 表示未开启回血。
            - ``heal_amount``: 每次回血恢复的血量。
        dt: 本帧耗时(秒),由游戏循环传入,用于保证回血速度与帧率无关。

    Returns:
        None,直接原地修改 ``player_state``,不返回任何值。
    """
    # 防御:状态为空(未初始化或传入 None)时不做任何处理,避免崩溃。
    if not player_state:
        return

    interval = player_state.get("heal_interval", 0)
    # 未开启回血(快速模式)或间隔非法,直接返回。
    if interval <= 0:
        return

    max_hp = player_state.get("max_hp", 0)
    # 最大血量非法时无法结算,直接返回。
    if max_hp <= 0:
        return

    hp = player_state.get("hp", max_hp)
    # 死亡(<=0)或满血(>=max_hp)都无需回血,直接返回。
    if hp <= 0 or hp >= max_hp:
        return

    timer = player_state.get("heal_timer", interval)
    timer -= dt

    # 倒计时归零:回一次血,并把倒计时重置回满间隔。
    if timer <= 0:
        heal_amount = player_state.get("heal_amount", 0)
        player_state["hp"] = min(hp + heal_amount, max_hp)
        timer = interval

    player_state["heal_timer"] = timer
