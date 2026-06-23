import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="🛡️ 工業級動態防禦退休精算器 v4", layout="wide")

st.title("🛡️ 工業級動態防禦退休精算器 v4")
st.write("本計算器將每一年度的現金流拆解至「按月精算」，並導入台灣在地化的多重通膨、週期性大筆支出及政府年金銜接模型。")

st.markdown("---")

st.header("⚙️ 核心評估參數設定")

# 1. 基本資訊
st.subheader("👤 基本資訊")
col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input("目前年齡 (歲)", min_value=1, max_value=100, value=37, step=1)
    retire_age = st.number_input("預計退休年齡 (歲)", min_value=current_age, max_value=100, value=40, step=1)
with col2:
    target_age = st.number_input("預計活到幾歲", min_value=retire_age, max_value=110, value=100, step=1)
    current_assets = st.number_input("目前資產總額 (新台幣/元)", min_value=0, value=48000000, step=1000000, format="%d")

# 2. 支出分流設定
st.subheader("💰 支出與生活水平")
col3, col4 = st.columns(2)
with col3:
    base_monthly_expense = st.number_input("退休後每月基礎基本支出 (目前幣值/元)", min_value=0, value=166667, step=5000, format="%d")
    medical_monthly_expense_60 = st.number_input("60歲後每月額外醫療/長照預備金 (目前幣值/元)", min_value=0, value=30000, step=5000, format="%d")
with col4:
    capital_expense_cycle = st.number_input("非經常性大筆支出週期 (例如：每幾年換車或大修房屋)", min_value=1, max_value=30, value=10, step=1)
    capital_expense_amount = st.number_input("非經常性大筆支出每次金額 (元)", min_value=0, value=1500000, step=100000, format="%d")

# 3. 市場與風險控制（加入台灣環境備註）
st.subheader("📈 市場與通膨參數 (附台灣環境標準參考)")
roi_core = st.slider(
    "核心資產池預期年化報酬率 (%) —— 💡 台灣大盤與平衡型組合長期合理區間：4.0% ~ 8.0%", 
    min_value=0.0, max_value=15.0, value=6.0, step=0.5
) / 100

inflation_general = st.slider(
    "一般物價通膨率 (%) —— 💡 台灣主計總處與體感通膨長期穩健區間：1.5% ~ 2.5%", 
    min_value=0.0, max_value=10.0, value=2.0, step=0.1
) / 100

inflation_medical = st.slider(
    "醫療費用獨立通膨率 (%) —— 💡 台灣自費醫療、高級醫材與長照費用非線性漲幅區間：4.0% ~ 6.0%", 
    min_value=0.0, max_value=10.0, value=4.5, step=0.1
) / 100

# 改為0.5年為調整單位
cash_buffer_years = st.slider(
    "防禦性現金緩衝池大小 (預留幾年生活費) —— 💡 建議至少預留 2.0 ~ 3.0 年以完全規避台股序列報酬風險", 
    min_value=0.0, max_value=5.0, value=3.0, step=0.5
)

# 4. 台灣社福銜接
st.subheader("🏦 台灣社會福利年金銜接")
col5, col6 = st.columns(2)
with col5:
    gov_pension_age = st.number_input("預計請領政府年金（勞保+勞退）年齡", min_value=60, max_value=75, value=65, step=1)
with col6:
    gov_pension_amount = st.number_input("預估該年齡可領取之每月年金 (目前幣值/元)", min_value=0, value=25000, step=1000, format="%d")

st.markdown("---")

# --- 核心精算邏輯（以月為基準單位） ---
if current_assets > 0 and base_monthly_expense > 0 and retire_age >= current_age:
    years_to_retire = retire_age - current_age
    months_to_retire = years_to_retire * 12
    total_retirement_months = (target_age - retire_age) * 12

    # A. 退休當期受通膨調整後的首月支出與所需的防禦現金池
    first_month_expense_inflated = base_monthly_expense * ((1 + inflation_general) ** years_to_retire)
    total_cash_buffer_needed = (first_month_expense_inflated * 12) * cash_buffer_years

    # B. 月度級現金流模擬演算函數
    def run_monthly_simulation(monthly_save):
        # 衝刺期複利滾存（按月）
        assets = current_assets
        r_month_core = roi_core / 12
        for m in range(months_to_retire):
            assets = (assets * (1 + r_month_core)) + monthly_save
            
        final_ret_assets = assets
        core_pool = assets - total_cash_buffer_needed
        cash_pool = total_cash_buffer_needed
        
        history = []
        is_broken = False
        broken_age = None
        
        # 初始通膨基礎
        c_month_base = base_monthly_expense * ((1 + inflation_general) ** years_to_retire)
        c_month_med = medical_monthly_expense_60 * ((1 + inflation_medical) ** (60 - current_age)) if retire_age <= 60 else medical_monthly_expense_60 * ((1 + inflation_medical) ** years_to_retire)
        c_gov_pension = gov_pension_amount * ((1 + inflation_general) ** (gov_pension_age - current_age))
        
        for m in range(total_retirement_months + 1):
            current_retire_year = m // 12
            current_retire_month_idx = m % 12
            age = retire_age + current_retire_year
            
            total_wealth = core_pool + cash_pool
            if total_wealth < 0 and not is_broken:
                is_broken = True
                broken_age = age
            
            # 1. 每月支出計算
            expense = c_month_base
            if age >= 60:
                expense += c_month_med
                
            # 每隔 X 年在退休周年的首月發生大筆資本支出
            if m > 0 and (m % (capital_expense_cycle * 12) == 0):
                expense += capital_expense_amount * ((1 + inflation_general) ** (years_to_retire + current_retire_year))
                
            # 2. 每月政府年金流入
            income = c_gov_pension if age >= gov_pension_age else 0
            net_drain = expense - income
            
            # 3. 水庫提領邏輯
            if cash_pool >= net_drain:
                cash_pool -= net_drain
            else:
                remaining_drain = net_drain - cash_pool
                cash_pool = 0
                core_pool -= remaining_drain
                
            # 4. 核心池月度複利
            roi_earnings = core_pool * r_month_core if core_pool > 0 else 0
            if core_pool > 0:
                core_pool += roi_earnings
                
            # 5. 紀錄月度流量表
            history.append({
                "年齡": f"{age}歲 {current_retire_month_idx + 1}個月",
                "期初總資產": total_wealth,
                "本月基本支出": c_month_base,
                "本月醫療預備金": c_month_med if age >= 60 else 0,
                "本月大筆資本支出": capital_expense_amount * ((1 + inflation_general) ** (years_to_retire + current_retire_year)) if (m > 0 and m % (capital_expense_cycle * 12) == 0) else 0,
                "本月政府年金流入": income,
                "核心投資池月收益": roi_earnings,
                "期末總資產": core_pool + cash_pool
            })
            
            # 每到新的一年（12個月），調升支出通膨率
            if current_retire_month_idx == 11:
                c_month_base *= (1 + inflation_general)
                if age >= 60:
                    c_month_med *= (1 + inflation_medical)
                    
        return not is_broken, history, final_ret_assets, broken_age

    # 二分法精確搜索退休前「每月應存金額」
    low, high = 0, 5000000
    for _ in range(30):
        mid = (low + high) / 2
        success, _, _, _ = run_monthly_simulation(mid)
        if success:
            high = mid
        else:
            low = mid
    required_save = low if low > 100 else 0
    success_final, final_history, final_assets, broken_age = run_monthly_simulation(required_save)
    
    # 轉換為 DataFrame 並格式化數字（千分位、無小數點）
    df_res = pd.DataFrame(final_history)
    df_display = df_res.copy()
    for col in ["期初總資產", "本月基本支出", "本月醫療預備金", "本月大筆資本支出", "本月政府年金流入", "核心投資池月收益", "期末總資產"]:
        df_display[col] = df_display[col].apply(lambda x: f"{int(round(x)):,}")

    # --- 畫面結果呈現 ---
    st.subheader("🎉 全面精算報告與核心執行指標")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("退休前「每個月」需存入金額", f"{int(round(required_save)):,} 元", 
                  delta="資產非常充足，無儲蓄壓力" if required_save == 0 else "需補足衝刺儲蓄")
    with col_m2:
        st.metric(f"{retire_age}歲退休當天總資產目標", f"{int(round(final_assets)):,} 元")

    # 繪製走勢圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_res["年齡"], y=df_res["期初總資產"], mode='lines', name='動態資產總額走勢', line=dict(color='#2ecc71', width=3)))
    fig.update_layout(
        title="精細化月度資產動態走勢（應保證在設定終點年齡前曲線不墜入負值）",
        xaxis_title="時間軸 (年齡與月份)", yaxis_title="資產總額 (元)",
        template="plotly_white", hovermode="x"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 顯示科學診斷與策略建議區
    st.markdown("---")
    st.header("🔬 健全性科學診斷與資產策略防禦建議")
    
    # 動態觸發診斷文本
    if required_save > 0:
        st.error(f"❌ **防禦健全性警告**：若維持現有資產與零儲蓄，您的資產預計將在 **{broken_age} 歲左右** 提前耗盡，無法安穩支撐至 100 歲。主因在於 60 歲後高達 4.5% 的獨立醫療通膨，與每 {capital_expense_cycle} 年一次的非經常性大筆支出，產生了非線性財富侵蝕。")
    else:
        st.success(f"▲ **防禦健全性安全**：在當前設定下，您的既有資產經月度精算，能夠完美抵抗多重通膨與週期大筆支出，成功存活至 100 歲！退休當天請嚴格執行將 **{int(round(total_cash_buffer_needed)):,} 元** 鎖定於防禦性現金緩衝池。")
        
    st.markdown(f"""
    ### 🛡️ 系統核心防禦策略指引：
    1. **雙水庫動態提領調度**：
       退休當天撥出的 **{int(round(total_cash_buffer_needed)):,} 元** 現金緩衝池，其唯一核心任務是「阻絕序列報酬風險 (Sequence of Returns Risk)」。當退休後遭遇台股或全球市場大熊市時，前 {cash_buffer_years} 年的生活支出全數由現金池發放，禁止變賣任何處於低點的核心股票部位，給予核心資產充足的景氣復甦週期。
    2. **對抗 4.5% 醫療通膨的外部解法**：
       模型中後期最大的財富殺手並非日常外食，而是高齡自費醫療。與其在模型中無限提高儲蓄，更具槓桿效益的作法是在未來 3 年衝刺期內，將個人的**「實支實付型醫療險」與「不還本失能長照險」**防護網配置完全。利用確定的保費支出，鎖定極端大額的醫療自費衝擊。
    3. **非經常性资本支出的動態緩衝**：
       明細表中所精算的每 {capital_expense_cycle} 年一次的大筆支出（如換車或老屋大修），在真實世界中屬於「可延後支出」。若適逢市場系統性大跌，應主動將資本支出往後推延 12 至 24 個月，能大幅優化核心資產池的長期存活概率。
    """)

    # 5. 月度現金流量表
    st.markdown("---")
    st.subheader("📋 工程級每月動態現金流量明細表 (無小數點 / 千分位格式)")
    st.dataframe(df_display.set_index("年齡"), use_container_width=True)

else:
    st.warning("⏳ 請於上方自訂基本資產、年齡與支出數據，系統將自動啟動動態月度現金流精算。")
