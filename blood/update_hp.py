"""血量结算模块 —— 掉血 / 回血统一入口。

实现 ``update_hp`` 函数,对玩家血量施加一个增量(正数回血、负数掉血),
并将其钳位到 ``[0, max_hp]`` 区间;掉血时自动打断回血倒计时。

该函数是血量变化的总入口,命中伤害、回血结算等都经由它完成:

    - 掉血(``amount < 0``):钳位血量后调用 ``interrupt_heal`` 打断回血倒计时,
      实现「受击打断回血」;未开启回血时 ``interrupt_heal`` 内部会直接跳过。
    - 回血(``amount > 0``):仅做钳位,不会误打断回血。
"""

try:
    from .interrupt_heal import interrupt_heal
except ImportError:  # 兼容把该文件当作独立模块直接导入的场景
    from blood.interrupt_heal import interrupt_heal


def update_hp(player_state, amount):
    """对玩家血量施加增量并钳位,掉血时打断回血。

    Args:
        player_state: 单个玩家的状态 ``dict``,需包含以下键:
            - ``hp``: 当前血量。
            - ``max_hp``: 最大血量。
            - (可选)``heal_interval``: 存在且 > 0 时表示开启回血,
              掉血时会触发回血打断;快速模式可省略该键。
        amount: 血量增量(浮点),正数回血、负数掉血。

    Returns:
        None,直接原地修改 ``player_state``,不返回任何值。
    """
    # 防御:状态为空(未初始化或传入 None)时不做任何处理,避免崩溃。
    if not player_state:
        return

    max_hp = player_state.get("max_hp", 0)
    # 最大血量非法时无法结算,直接返回。
    if max_hp <= 0:
        return

    hp = player_state.get("hp", max_hp)
    # 施加增量并钳位到 [0, max_hp],避免负血量或超上限。
    player_state["hp"] = max(0.0, min(hp + amount, max_hp))

    # 掉血时打断回血:受击后需重新等待完整回血间隔才能继续回血。
    # 是否开启回血由 interrupt_heal 内部判断,快速模式会自动跳过。
    if amount < 0:
        interrupt_heal(player_state)
