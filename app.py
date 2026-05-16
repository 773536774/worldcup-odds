import streamlit as st
import random

# 页面配置
st.set_page_config(page_title="世界杯赔率计算器", layout="wide")
st.title("⚽ 世界杯动态赔率结算")
st.markdown("### TEST")
st.divider()

# ======================
# 侧边栏：所有参数可调
# ======================
with st.sidebar:
    st.header("⚙️ 核心参数可调")
    base_win = st.number_input("主队胜基础赔率", 1.0, 20.0, 1.49, 0.01)
    base_draw = st.number_input("平局基础赔率", 1.0, 20.0, 4.63, 0.01)
    base_lose = st.number_input("客队胜基础赔率", 1.0, 20.0, 8.85, 0.01)

    st.subheader("固定系数")
    C = st.number_input("系数C", 0.5, 2.0, 0.92, 0.01)
    beta = st.number_input("热度系数β", 0.1, 1.0, 0.3, 0.01)
    R_MIN = st.number_input("随机系数最小值", 0.8, 1.2, 0.95, 0.01)
    R_MAX = st.number_input("随机系数最大值", 0.8, 1.2, 1.05, 0.01)
    ODDS_MIN = st.number_input("赔率下限", 1.0, 5.0, 1.05, 0.01)
    ODDS_MAX = st.number_input("赔率上限", 5.0, 50.0, 10.0, 0.1)

    st.subheader("平台风控")
    K = st.number_input("基础抽水K", 0.5, 1.0, 0.95, 0.01)
    K_RISK = st.number_input("极端风控系数", 0.5, 1.0, 0.7, 0.01)
    RISK_THRESHOLD = st.number_input("极端风控触发阈值(单选项占比)", 0.5, 1.0, 0.8, 0.01)
    PAYOUT_LIMIT_RATIO = st.number_input("赔付封顶比例", 0.5, 1.0, 0.98, 0.01)

    st.subheader("竞猜保险")
    INSURANCE_A = st.number_input("保险费率A%", 0.01, 0.5, 0.10, 0.01)
    INSURANCE_X_WIN = st.number_input("猜对额外获得X_win%", 0.01, 0.5, 0.05, 0.01)
    INSURANCE_X_LOSE = st.number_input("猜错返还X_lose%", 0.01, 0.5, 0.20, 0.01)

# ======================
# 下注数据输入
# ======================
st.subheader("💰 输入下注金额（英文逗号分隔）")
c1, c2, c3 = st.columns(3)
with c1:
    win_input = st.text_input("押主队胜", "100,200,150,1000,2000,10000")
with c2:
    draw_input = st.text_input("押平局", "50,80,500,1000")
with c3:
    lose_input = st.text_input("押客队胜", "30,60,40,90,100")

# 竞猜保险开关
st.subheader("🛡️ 竞猜保险")
enable_insurance = st.checkbox("启用竞猜保险（所有下注均购买保险）")
if enable_insurance:
    st.info(f"保险费率{INSURANCE_A*100:.0f}% | 猜对额外+{INSURANCE_X_WIN*100:.0f}% | 猜错返还{INSURANCE_X_LOSE*100:.0f}%")

# 解析输入
def get_bets(s):
    try:
        return [float(i.strip()) for i in s.split(",") if i.strip()]
    except:
        return []

win_bets = get_bets(win_input)
draw_bets = get_bets(draw_input)
lose_bets = get_bets(lose_input)

# ======================
# 比赛结果选择
# ======================
st.subheader("🏆 比赛结果")
MATCH_RESULT = st.radio("", ["win", "draw", "lose"], horizontal=True)
st.divider()

# ======================
# 计算逻辑
# ======================
def calculate_dynamic_odds(base_odds, total_stake, stake_item, all_stakes_list):
    """
    新公式: Ofinal = clamp(Obase * C * H * R * K, ODDS_MIN, ODDS_MAX)
    H = 1 + β * (si/Stotal - 1/n), n=3
    当任意选项占比 > RISK_THRESHOLD 时启用 K_RISK
    """
    n = 3  # 选项数
    R = random.uniform(R_MIN, R_MAX)

    # 热度系数 H = 1 + β * (si/Stotal - 1/n)
    heat_ratio = stake_item / total_stake if total_stake > 0 else 1.0 / n
    H = 1 + beta * (heat_ratio - 1.0 / n)

    # 判断是否触发极端风控（任意单选项占比超过阈值）
    max_ratio = max(s / total_stake for s in all_stakes_list) if total_stake > 0 else 0
    current_K = K_RISK if max_ratio > RISK_THRESHOLD else K

    raw_odds = base_odds * C * H * R * current_K
    final_odds = max(ODDS_MIN, min(raw_odds, ODDS_MAX))

    return round(final_odds, 2), round(R, 3), round(H, 3), current_K == K_RISK


def calculate_insurance(bet_amount, is_correct):
    """
    竞猜保险计算
    保险费 = 下注额 * A%
    猜对：额外获得 = 下注额 * X_win%
    猜错：返还 = 下注额 * X_lose%
    """
    insurance_cost = bet_amount * INSURANCE_A
    if is_correct:
        bonus = bet_amount * INSURANCE_X_WIN
        net_insurance = bonus - insurance_cost
        return insurance_cost, bonus, net_insurance
    else:
        refund = bet_amount * INSURANCE_X_LOSE
        net_insurance = refund - insurance_cost
        return insurance_cost, refund, net_insurance


def settle_bets(bet_list, odds, result_type, target_type, total_stake, has_insurance=False):
    rewards = []
    insurance_details = []
    max_total_payout = total_stake * PAYOUT_LIMIT_RATIO
    is_payout_limit = False

    if result_type == target_type:
        is_correct = True
        raw_rewards = [round(bet * odds, 2) for bet in bet_list]
        total_raw = sum(raw_rewards)
        if total_raw > max_total_payout:
            is_payout_limit = True
            shrink_ratio = max_total_payout / total_raw
            rewards = [round(r * shrink_ratio, 2) for r in raw_rewards]
        else:
            rewards = raw_rewards

        # 保险计算（猜对）
        if has_insurance:
            for i, bet in enumerate(bet_list):
                ins_cost, ins_bonus, ins_net = calculate_insurance(bet, is_correct)
                insurance_details.append({
                    "bet": bet,
                    "reward": rewards[i],
                    "ins_cost": round(ins_cost, 2),
                    "ins_gain": round(ins_bonus, 2),
                    "ins_net": round(ins_net, 2),
                    "total_with_ins": round(rewards[i] + ins_net, 2),
                })
    else:
        is_correct = False
        rewards = [0.0] * len(bet_list)

        # 保险计算（猜错）
        if has_insurance:
            for i, bet in enumerate(bet_list):
                ins_cost, ins_refund, ins_net = calculate_insurance(bet, is_correct)
                insurance_details.append({
                    "bet": bet,
                    "reward": 0.0,
                    "ins_cost": round(ins_cost, 2),
                    "ins_gain": round(ins_refund, 2),
                    "ins_net": round(ins_net, 2),
                    "total_with_ins": round(ins_net, 2),  # 猜错只有保险净收益
                })

    return rewards, is_payout_limit, insurance_details


# 统计
total_win = sum(win_bets)
total_draw = sum(draw_bets)
total_lose = sum(lose_bets)
total_stake = total_win + total_draw + total_lose

all_stakes = [total_win, total_draw, total_lose]

# 计算赔率
win_odds, R_win, H_win, is_risk = calculate_dynamic_odds(base_win, total_stake, total_win, all_stakes)
draw_odds, R_draw, H_draw, _ = calculate_dynamic_odds(base_draw, total_stake, total_draw, all_stakes)
lose_odds, R_lose, H_lose, _ = calculate_dynamic_odds(base_lose, total_stake, total_lose, all_stakes)

# 结算
win_rewards, is_win_limit, win_ins = settle_bets(win_bets, win_odds, MATCH_RESULT, "win", total_stake, enable_insurance)
draw_rewards, is_draw_limit, draw_ins = settle_bets(draw_bets, draw_odds, MATCH_RESULT, "draw", total_stake, enable_insurance)
lose_rewards, is_lose_limit, lose_ins = settle_bets(lose_bets, lose_odds, MATCH_RESULT, "lose", total_stake, enable_insurance)

# 计算总收益
total_reward_base = round(sum(win_rewards) + sum(draw_rewards) + sum(lose_rewards), 2)

if enable_insurance:
    total_insurance_cost = sum(b * INSURANCE_A for b in win_bets + draw_bets + lose_bets)
    total_ins_net = 0
    for details in [win_ins, draw_ins, lose_ins]:
        for d in details:
            total_ins_net += d["ins_net"]
    total_reward_with_ins = round(total_reward_base + total_ins_net, 2)
    platform_profit = round(total_stake + total_insurance_cost - total_reward_with_ins, 2)
else:
    total_reward_with_ins = total_reward_base
    platform_profit = round(total_stake - total_reward_base, 2)

# 隐含概率
implied_prob = round(1 / win_odds + 1 / draw_odds + 1 / lose_odds, 3)

# ======================
# 结果展示
# ======================
st.subheader("📊 计算结果")

if enable_insurance:
    a, b, c, d, e = st.columns(5)
    a.metric("总押注金额", f"{total_stake:,.0f}")
    b.metric("总保险费", f"{total_insurance_cost:,.0f}")
    c.metric("基础奖金", f"{total_reward_base:,.0f}")
    d.metric("含保险总奖金", f"{total_reward_with_ins:,.0f}")
    e.metric("平台净收益", f"{platform_profit:,.0f}")
else:
    a, b, c = st.columns(3)
    a.metric("总押注金额", f"{total_stake:,.0f}")
    b.metric("用户总奖金", f"{total_reward_base:,.0f}")
    c.metric("平台净收益", f"{platform_profit:,.0f}")

st.markdown("#### 📈 最终赔率")
col1, col2, col3 = st.columns(3)
col1.write(f"**主队胜：{win_odds}** (R={R_win}, H={H_win})")
col2.write(f"**平局：{draw_odds}** (R={R_draw}, H={H_draw})")
col3.write(f"**客队胜：{lose_odds}** (R={R_lose}, H={H_lose})")
st.write(f"隐含概率：{implied_prob} (抽水 {(implied_prob - 1) * 100:.1f}%)")

if is_risk:
    st.warning(f"⚠️ 触发极端风控 K_RISK={K_RISK}（单选项占比>{RISK_THRESHOLD * 100:.0f}%）")

any_limit = is_win_limit or is_draw_limit or is_lose_limit
if any_limit:
    st.info(f"⚠️ 触发赔付上限(封顶比例{PAYOUT_LIMIT_RATIO})，奖励已按比例缩减")

# 收益明细
st.markdown("#### 🎯 收益明细")

label_map = {"主队胜": "win", "平局": "draw", "客队胜": "lose"}
for label, bets, rewards, ins_details, is_limit in [
    ("主队胜", win_bets, win_rewards, win_ins, is_win_limit),
    ("平局", draw_bets, draw_rewards, draw_ins, is_draw_limit),
    ("客队胜", lose_bets, lose_rewards, lose_ins, is_lose_limit),
]:
    is_winner = (MATCH_RESULT == label_map[label])
    limit_tag = " 🔒封顶缩减" if is_limit else ""
    win_tag = " ✅猜对" if is_winner else " ❌猜错"

    if not enable_insurance:
        st.write(f"**{label}** {len(bets)}人{win_tag}{limit_tag}：{[round(b, 0) for b in bets]} → {[round(r, 2) for r in rewards]}")
    else:
        st.write(f"**{label}** {len(bets)}人{win_tag}{limit_tag}：")
        ins_gain_label = "保险额外" if is_winner else "保险返还"
        header = f"| 下注 | 基础奖金 | 保险费({INSURANCE_A*100:.0f}%) | {ins_gain_label} | 保险净收益 | 合计到手 |"
        separator = "|---:|---:|---:|---:|---:|---:|"
        st.markdown(header)
        st.markdown(separator)
        for d in ins_details:
            net_sign = "+" if d["ins_net"] >= 0 else ""
            row = f"| {d['bet']:,.0f} | {d['reward']:,.2f} | -{d['ins_cost']:,.2f} | {d['ins_gain']:,.2f} | {net_sign}{d['ins_net']:,.2f} | {d['total_with_ins']:,.2f} |"
            st.markdown(row)

# 押注热度分布
st.markdown("#### 📊 押注热度分布")
if total_stake > 0:
    heat_col1, heat_col2, heat_col3 = st.columns(3)
    heat_col1.write(f"主队胜：{total_win:,.0f} ({total_win / total_stake * 100:.1f}%) → H={H_win}")
    heat_col2.write(f"平局：{total_draw:,.0f} ({total_draw / total_stake * 100:.1f}%) → H={H_draw}")
    heat_col3.write(f"客队胜：{total_lose:,.0f} ({total_lose / total_stake * 100:.1f}%) → H={H_lose}")
    st.write(f"H系数公式：1 + {beta} × (占比 - 1/3)")
