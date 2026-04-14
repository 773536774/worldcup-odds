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
    R_MIN = st.number_input("随机系数最小值", 0.8, 1.2, 0.95, 0.01)
    R_MAX = st.number_input("随机系数最大值", 0.8, 1.2, 1.05, 0.01)
    ODDS_MIN = st.number_input("赔率下限", 1.0, 5.0, 1.05, 0.01)
    ODDS_MAX = st.number_input("赔率上限", 5.0, 50.0, 10.0, 0.1)

    st.subheader("平台风控")
    K = st.number_input("基础抽水K", 0.5, 1.0, 0.95, 0.01)
    K_RISK = st.number_input("极端风控系数", 0.5, 1.0, 0.7, 0.01)
    PAYOUT_LIMIT_RATIO = st.number_input("赔付封顶比例", 0.5, 1.0, 0.98, 0.01)

# ======================
# 下注数据输入
# ======================
st.subheader("💰 输入下注金额（英文逗号分隔）")
c1, c2, c3 = st.columns(3)
with c1: win_input = st.text_input("押主队胜", "100,200,150,1000,2000,10000")
with c2: draw_input = st.text_input("押平局", "50,80,500,1000")
with c3: lose_input = st.text_input("押客队胜", "30,60,40,90,100")

# 解析输入
def get_bets(s):
    try: return [float(i.strip()) for i in s.split(",") if i.strip()]
    except: return []
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
# 原计算逻辑（完全保留）
# ======================
def calculate_dynamic_odds(base_odds, total_stake, stake_item, option_name):
    R = random.uniform(R_MIN, R_MAX)
    heat_ratio = stake_item / total_stake if total_stake > 0 else 0.0
    current_K = K_RISK if heat_ratio == 1.0 else K
    raw_odds = base_odds * (1 - heat_ratio) * R * C * current_K
    final_odds = max(ODDS_MIN, min(raw_odds, ODDS_MAX))
    return round(final_odds, 2), round(R, 3)

def settle_bets(bet_list, odds, result_type, target_type, total_stake):
    rewards = []
    max_total_payout = total_stake * PAYOUT_LIMIT_RATIO
    is_payout_limit = False
    if result_type == target_type:
        raw_rewards = [round(bet * odds, 2) for bet in bet_list]
        total_raw = sum(raw_rewards)
        if total_raw > max_total_payout:
            is_payout_limit = True
            shrink_ratio = max_total_payout / total_raw
            rewards = [round(r * shrink_ratio, 2) for r in raw_rewards]
        else:
            rewards = raw_rewards
    else:
        rewards = [0.0]*len(bet_list)
    return rewards, is_payout_limit

# 统计
total_win = sum(win_bets)
total_draw = sum(draw_bets)
total_lose = sum(lose_bets)
total_stake = total_win + total_draw + total_lose

# 计算赔率
win_odds, R_win = calculate_dynamic_odds(base_win, total_stake, total_win, "主队胜")
draw_odds, R_draw = calculate_dynamic_odds(base_draw, total_stake, total_draw, "平局")
lose_odds, R_lose = calculate_dynamic_odds(base_lose, total_stake, total_lose, "客队胜")

# 结算
win_rewards, is_win_limit = settle_bets(win_bets, win_odds, MATCH_RESULT, "win", total_stake)
draw_rewards, _ = settle_bets(draw_bets, draw_odds, MATCH_RESULT, "draw", total_stake)
lose_rewards, _ = settle_bets(lose_bets, lose_odds, MATCH_RESULT, "lose", total_stake)

total_reward = round(sum(win_rewards)+sum(draw_rewards)+sum(lose_rewards),2)
platform_profit = round(total_stake - total_reward,2)

# ======================
# 结果展示
# ======================
st.subheader("📊 计算结果")
a,b,c = st.columns(3)
a.metric("总押注积分", total_stake)
b.metric("用户总奖金", total_reward)
c.metric("平台净收益", platform_profit)

st.markdown("#### 📈 最终赔率")
st.write(f"主队胜：{win_odds} (随机系数 {R_win})")
st.write(f"平局：{draw_odds} (随机系数 {R_draw})")
st.write(f"客队胜：{lose_odds} (随机系数 {R_lose})")

if is_win_limit:
    st.info("⚠️ 触发赔付上限，奖励已按比例缩减")

st.markdown("#### 🎯 收益明细")
st.write(f"主队胜 {len(win_bets)} 人：{win_bets} → {win_rewards}")
st.write(f"平局 {len(draw_bets)} 人：{draw_bets} → {draw_rewards}")
st.write(f"客队胜 {len(lose_bets)} 人：{lose_bets} → {lose_rewards}")
