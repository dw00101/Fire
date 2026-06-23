import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="🛡️ 工業級動態防禦退休計算器", layout="centered")

st.title("🛡️ 工業級動態防禦退休計算器")
st.write("請輸入您的個人參數。本計算器採用多重風險防禦模型，精算退休前應儲蓄額與動態現金流。")

st.markdown("---")

st.header("⚙️ 核心參數自訂區")

# 1. 基本資訊
st.subheader("👤 基本資訊")
col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input("目前年齡 (歲)", min_value=1, max_value=100, value=1, step=1)
    retire_age = st.number_input("預計退休年齡 (歲)", min_value=1, max_value=100, value=2, step=1)
with col2:
    target_age = st.number_input("預計活到幾歲", min_value=2, max_value=110, value=100, step=1)
    current_assets = st.number_input("目前資產總額 (新台幣/元)", min_value=0, value=0, step=100000)

# 2. 支出分流設定
st.subheader("💰 支出與生活水平")
base_monthly_expense = st.number_input("退休後每月基礎基本支出 (目前幣值/元)", min_value=0, value=0, step=5000)
medical_monthly_expense_60 = st.number_input("60歲後每月額外醫療/長照預備金 (目前幣值/元)", min_value=0, value=0, step=5000)
capital_expense_cycle = st.number_input("非經常性大筆支出週期 (例如：每幾年換車或大修房屋)", min_value=1, max_value=30, value=10, step=1)
capital_expense_amount = st.number_input("非經常性大筆支出每次金額 (元)", min_value=0, value=0, step=100000)

# 3. 市場與風險控制
st.subheader("📈 市場與通膨參數")
roi_core = st.slider("核心資產池預期年化報酬率 (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.1) / 100
inflation_general = st.slider("一般物價通膨率 (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1) / 100
inflation_medical = st.slider("醫療費用獨立通膨率 (%)", min_value=0.0, max_value=10.0, value=4.0, step=0.1) / 100
cash_buffer_years = st.slider("防禦性現金緩衝池大小 (預留幾年生活費)", min_value=0, max_value=5, value=3, step=1)

# 4. 台灣社福銜接
st.subheader("🏦 社會福利年金銜接")
gov_pension_age = st.number_input("預計請領政府年金（勞保+勞退）年齡", min_value=60, max_value=75, value=65, step=1)
gov_pension_amount = st.number_input("預估該年齡可領取之每月年金 (目前幣值/元)", min_value=0, value=0, step=1000)

st.markdown("---")

# 計算控制鎖：確保輸入合理數值才開始計算
if current_assets > 0 and base_monthly_expense > 0 and retire_age > current_age:
    years_to_retire = retire_age - current_age
    retirement_years = target_age - retire_age

    # A. 現金池計算
    first_year_expense_inflated = (base_monthly_expense * 12) * ((1 + inflation_general) ** years_to_retire)
    total_cash_buffer_needed = first_year_expense_inflated * cash_buffer_years

    # B. 模擬核心演算
    def run_simulation(monthly_save):
        assets = current_assets
        for _ in range(years_to_retire):
            assets = (assets * (1 + roi_core)) + (monthly_save * 12)
        
        final_ret_assets = assets
        core_pool = assets - total_cash_buffer_needed
        cash_pool = total_cash_buffer_needed
        
        c_annual_base = base_monthly_expense * 12 * ((1 + inflation_general) ** years_to_retire)
        c_annual_med = medical_monthly_expense_60 * 12 * ((1 + inflation_medical) ** (60 - current_age)) if retire_age <= 60 else medical_monthly_expense_60 * 12 * ((1 + inflation_medical) ** years_to_retire)
        c_gov_pension = gov_pension_amount * 12 * ((1 + inflation_general) ** (gov_pension_age - current_age))
        
        success = True
        history = []
        
        for year in range(retirement_years + 1):
            age = retire_age + year
            total_wealth = core_pool + cash_pool
            if total_wealth < 0:
                success = False
            
            expense = c_annual_base
            if age >= 60:
                expense += c_annual_med
            if (year > 0) and (year % capital_expense_cycle == 0):
                expense += capital_expense_amount * ((1 + inflation_general) ** (years_to_retire + year))
                
            income = c_gov_pension if age >= gov_pension_age else 0
            net_drain = expense - income
            
            if cash_pool >= net_drain:
                cash_pool -= net_drain
            else:
                remaining_drain = net_drain - cash_pool
                cash_pool = 0
                core_pool -= remaining_drain
                
            roi_earnings = core_pool * roi_core if core_pool > 0 else 0
            if core_pool > 0:
                core_pool += roi_earnings
                
            history.append({
                "年齡": age,
                "期初總資產": total_wealth,
                "每月基礎支出": c_annual_base / 12,
                "每月醫療預備": (c_annual_med / 12) if age >= 60 else 0,
                "當年度大筆支出": (capital_expense_amount * ((1 + inflation_general) ** (years_to_retire + year))) if (year > 0 and year % capital_expense_cycle == 0) else 0,
                "每月政府年金": income / 12,
                "期末總資產": core_pool + cash_pool
            })
            
            c_annual_base *= (1 + inflation_general)
            if age >= 60:
                c_annual_med *= (1 + inflation_medical)
                
        return success, history, final_ret_assets

    # 二分法尋找每月儲蓄額
    low, high = 0, 5000000
    for _ in range(30):
        mid = (low + high) / 2
        success, _, _ = run_simulation(mid)
        if success:
            high = mid
        else:
            low = mid
    required_save = low if low > 100 else 0
    _, final_history, final_assets = run_simulation(required_save)
    df_res = pd.DataFrame(final_history)

    # 顯示結果
    st.subheader("🎉 評估指標結果")
    st.metric("退休前每個月需存入金額", f"{required_save:,.0f} 元")
    st.metric("退休當天總資產目標", f"{final_assets:,.0f} 元")
    
    # 畫圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_res["年齡"], y=df_res["期初總資產"], mode='lines', name='防禦動態總資產'))
    st.plotly_chart(fig, use_container_width=True)
    
    # 現金流量表
    st.subheader("📋 每月動態現金流量明細表")
    st.dataframe(df_res.set_index("年齡"), use_container_width=True)
else:
    st.warning("⏳ 請於上方填寫完整的年齡、資產與支出數據，系統將自動啟動動態現金流演算。")
