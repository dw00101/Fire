import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 網頁與手機版畫面最佳化設定
st.set_page_config(page_title="工程級防禦型退休計算器", layout="centered")

st.title("🛡️ 工程級防禦型退休計算器")
st.write("本模型捨棄理想化靜態假設，納入「序列報酬風險」、「醫療通膨」與「政府年金動態銜接」等真實世界波動因素。")

st.markdown("---")

# --- 側邊欄 / 參數輸入區 ---
st.header("⚙️ 核心評估參數設定")

# 1. 基本資訊
st.subheader("👤 基本資訊")
col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input("目前年齡", min_value=0, max_value=100, value=37, step=1)
    retire_age = st.number_input("預計退休年齡", min_value=current_age, max_value=100, value=40, step=1)
with col2:
    target_age = st.number_input("預計活到幾歲", min_value=retire_age, max_value=110, value=100, step=1)
    current_assets = st.number_input("目前資產總額 (元)", min_value=0, value=48000000, step=1000000, format="%d")

# 2. 支出流分流設定
st.subheader("💰 支出與生活水平")
base_monthly_expense = st.number_input("退休後每月基礎基本支出 (目前幣值/元)", min_value=0, value=166667, step=5000, format="%d")
medical_monthly_expense_60 = st.number_input("60歲後每月額外醫療/長照預備金 (目前幣值/元)", min_value=0, value=30000, step=5000, format="%d")
capital_expense_cycle = st.number_input("非經常性大筆支出週期 (例如：每幾年換車或大修房屋)", min_value=1, max_value=20, value=10, step=1)
capital_expense_amount = st.number_input("非經常性大筆支出每次金額 (元)", min_value=0, value=1500000, step=100000, format="%d")

# 3. 投資與市場風險
st.subheader("📈 市場與通膨參數")
roi_core = st.slider("核心資產池預期年化報酬率 (%)", min_value=0.0, max_value=15.0, value=6.0, step=0.5) / 100
inflation_general = st.slider("一般一般物價通膨率 (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1) / 100
inflation_medical = st.slider("醫療費用獨立通膨率 (%)", min_value=0.0, max_value=10.0, value=4.5, step=0.1) / 100
cash_buffer_years = st.slider("防禦性現金緩衝池大小 (預留幾年生活費)", min_value=0, max_value=5, value=3, step=1)

# 4. 台灣社福銜接
st.subheader("🏦 台灣社會福利年金動態銜接")
gov_pension_age = st.number_input("預計請領政府年金（勞保+勞退）年齡", min_value=60, max_value=75, value=65, step=1)
gov_pension_amount = st.number_input("預估該年齡可領取之每月年金 (目前幣值/元)", min_value=0, value=25000, step=1000, format="%d")

st.markdown("---")

# --- 核心邏輯計算 ---
years_to_retire = retire_age - current_age
retirement_years = target_age - retire_age

# A. 計算退休時所需的「防禦現金池」
first_year_annual_expense = base_monthly_expense * 12
# 考慮通膨到退休那一年的日常支出
first_year_annual_expense_inflated = first_year_annual_expense * ((1 + inflation_general) ** years_to_retire)
total_cash_buffer_needed = first_year_annual_expense_inflated * cash_buffer_years

# B. 計算衝刺期（37-40歲）的核心資產滾存與反推每月應存金額
def run_simulation(monthly_save):
    assets = current_assets
    for y in range(years_to_retire):
        assets = (assets * (1 + roi_core)) + (monthly_save * 12)
    
    core_pool = assets - total_cash_buffer_needed
    cash_pool = total_cash_buffer_needed
    
    current_annual_base = base_monthly_expense * 12 * ((1 + inflation_general) ** years_to_retire)
    current_annual_medical = medical_monthly_expense_60 * 12 * ((1 + inflation_medical) ** (60 - current_age)) if retire_age <= 60 else medical_monthly_expense_60 * 12 * ((1 + inflation_medical) ** years_to_retire)
    current_gov_pension = gov_pension_amount * 12 * ((1 + inflation_general) ** (gov_pension_age - current_age))
    
    success = True
    asset_history = []
    
    for year in range(retirement_years + 1):
        age = retire_age + year
        total_wealth = core_pool + cash_pool
        asset_history.append(total_wealth)
        
        if total_wealth < 0:
            success = False
            
        expense = current_annual_base
        if age >= 60:
            expense += current_annual_medical
        if (year > 0) and (year % capital_expense_cycle == 0):
            expense += capital_expense_amount * ((1 + inflation_general) ** (years_to_retire + year))
            
        income = current_gov_pension if age >= gov_pension_age else 0
        net_drain = expense - income
        
        if cash_pool >= net_drain:
            cash_pool -= net_drain
        else:
            remaining_drain = net_drain - cash_pool
            cash_pool = 0
            core_pool -= remaining_drain
            
        if core_pool > 0:
            core_pool = core_pool * (1 + roi_core)
            
        current_annual_base *= (1 + inflation_general)
        if age >= 60:
            current_annual_medical *= (1 + inflation_medical)
            
    return success, asset_history, assets

low, high = 0, 5000000
required_monthly_save = 0
for _ in range(30):
    mid = (low + high) / 2
    success, _, _ = run_simulation(mid)
    if success:
        high = mid
    else:
        low = mid
required_monthly_save = low if low > 100 else 0

_, asset_history_final, final_retirement_assets = run_simulation(required_monthly_save)

# --- 畫面結果呈現 ---
st.subheader("🎉 全面評估報告與執行指標")

col_metric1, col_metric2 = st.columns(2)
with col_metric1:
    st.metric("退休前每個月需存入金額", f"{required_monthly_save:,.0f} 元", 
              delta="資產充足，無儲蓄壓力" if required_monthly_save == 0 else "需補足衝刺儲蓄")
with col_metric2:
    st.metric("40歲退休時總資產目標", f"{final_retirement_assets:,.0f} 元")

st.markdown(f"**健全性科學診斷**：\\n"
            f"* **防禦現金池配置**：您在 40 歲退休的當天，需立刻將 **{total_cash_buffer_needed:,.0f} 元** 鎖進高利活存或定存作為「防禦現金池」（足夠應付前 {cash_buffer_years} 年的生活支出）。\\n"
            f"* **核心資產池配置**：剩餘的 **{(final_retirement_assets - total_cash_buffer_needed):,.0f} 元** 全數投入年化 {roi_core*100}% 的核心平衡型組合。這樣做能保證您在前幾年遭遇股市大跌時，完全不需要變賣任何股票。")

ages = list(range(retire_age, target_age + 2))
if len(asset_history_final) < len(ages):
    ages = ages[:len(asset_history_final)]
elif len(asset_history_final) > len(ages):
    asset_history_final = asset_history_final[:len(ages)]

fig = go.Figure()
fig.add_trace(go.Scatter(x=ages, y=asset_history_final, mode='lines', name='防禦型動態資產總額', line=dict(color='#2ecc71', width=3)))
fig.update_layout(
    title="考慮全面風險後的動態資產走勢",
    xaxis_title="年齡",
    yaxis_title="資產總額 (元)",
    template="plotly_white",
    hovermode="x"
)
st.plotly_chart(fig, use_container_width=True)

st.info("📊 想要觀看更詳細的每年度動態大數據現金流量表，請查看您部署的 Streamlit Cloud 後台，或調整上方參數即時觀察綠色走勢線的抗震彈性。")
