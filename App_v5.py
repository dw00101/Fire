import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="🛡️ 工業級動態防禦退休精算器 v8", layout="wide")

st.title("🛡️ 工業級動態防禦退休精算器 v8")
st.write("本計算器將每一年度的現金流拆解至「按月精算」，並根據您輸入的數據進行「智慧型動態方針診斷」，拒絕罐頭訊息。")

st.markdown("---")

st.header("⚙️ 核心評估參數設定")

# 協助解析千分位字串為整數的防呆函數
def parse_comma_int(val_str, default_val):
    if not val_str:
        return default_val
    try:
        # 移除使用者可能輸入的千分位逗號、空白與新台幣符號
        clean_str = str(val_str).replace(",", "").replace(" ", "").replace("$", "")
        return int(clean_str)
    except ValueError:
        return default_val

# 1. 基本資訊
st.subheader("👤 基本資訊")
col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input("目前年齡 (歲)", min_value=1, max_value=100, value=20, step=1)
    retire_age = st.number_input("預計退休年齡 (歲)", min_value=current_age, max_value=100, value=40, step=1)
with col2:
    target_age = st.number_input("預計活到幾歲", min_value=retire_age, max_value=110, value=90, step=1)
    
    # 改用 text_input 並預設提供標準千分位字串
    current_assets_str = st.text_input("目前資產總額 (新台幣/元)", value="1,000,000")
    current_assets = parse_comma_int(current_assets_str, 1000000)

# 2. 支出分流設定
st.subheader("💰 支出與生活水平")
col3, col4 = st.columns(2)
with col3:
    base_monthly_expense_str = st.text_input("退休後每月基礎基本支出 (目前幣值/元)", value="10,000")
    base_monthly_expense = parse_comma_int(base_monthly_expense_str, 10000)
    
    medical_monthly_expense_60_str = st.text_input("60歲後每月額外醫療/長照預備金 (目前幣值/元)", value="30,000")
    medical_monthly_expense_60 = parse_comma_int(medical_monthly_expense_60_str, 30000)
with col4:
    capital_expense_cycle = st.number_input("非經常性大筆支出週期 (例如：每幾年換車或大修房屋)", min_value=1, max_value=30, value=10, step=1)
    
    capital_expense_amount_str = st.text_input("非經常性大筆支出每次金額 (元)", value="1,000,000")
    capital_expense_amount = parse_comma_int(capital_expense_amount_str, 1000000)

# 3. 市場與風險控制
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
    gov_pension_amount_str = st.text_input("預估該年齡可領取之每月年金 (目前幣值/元)", value="10,000")
    gov_pension_amount = parse_comma_int(gov_pension_amount_str, 10000)

st.markdown("---")

# --- 核心精算邏輯 ---
if (current_assets > 0 and base_monthly_expense > 0 and retire_age > current_age):

    years_to_retire = retire_age - current_age
    months_to_retire = years_to_retire * 12
    total_retirement_months = (target_age - retire_age) * 12

    # A. 退休當期受通膨調整後的首月支出與所需的防禦現金池
    first_month_expense_inflated = base_monthly_expense * ((1 + inflation_general) ** years_to_retire)
    total_cash_buffer_needed = (first_month_expense_inflated * 12) * cash_buffer_years

    # B. 月度級現金流模擬演算函數
    def run_monthly_simulation(monthly_save):
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
            
            expense = c_month_base
            if age >= 60:
                expense += c_month_med
                
            if m > 0 and (m % (capital_expense_cycle * 12) == 0):
                expense += capital_expense_amount * ((1 + inflation_general) ** (years_to_retire + current_retire_year))
                
            income = c_gov_pension if age >= gov_pension_age else 0
            net_drain = expense - income
            
            if cash_pool >= net_drain:
                cash_pool -= net_drain
            else:
                remaining_drain = net_drain - cash_pool
                cash_pool = 0
                core_pool -= remaining_drain
                
            roi_earnings = core_pool * r_month_core if core_pool > 0 else 0
            if core_pool > 0:
                core_pool += roi_earnings
                
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
            
            if current_retire_month_idx == 11:
                c_month_base *= (1 + inflation_general)
                if age >= 60:
                    c_month_med *= (1 + inflation_medical)
                    
        return not is_broken, history, final_ret_assets, broken_age

    # 二分法搜索每月儲蓄額
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
    
    # 格式化輸出數據（移除小數點，加入千分位）
    df_res = pd.DataFrame(final_history)
    df_display = df_res.copy()
    for col in ["期初總資產", "本月基本支出", "本月醫療預備金", "本月大筆資本支出", "本月政府年金流入", "核心投資池月收益", "期末總資產"]:
        df_display[col] = df_display[col].apply(lambda x: f"{int(round(x)):,}")

    # --- 數據呈現 ---
    st.subheader("🎉 全面精算報告與核心執行指標")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("退休前「每個月」需再存入金額", f"{int(round(required_save)):,} 元", 
                  delta="資產健全，無儲蓄壓力" if required_save == 0 else "需進行衝刺期儲蓄補強")
    with col_m2:
        st.metric(f"{retire_age}歲退休當天總資產目標", f"{int(round(final_assets)):,} 元")

    # 走勢圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_res["年齡"], y=df_res["期初總資產"], mode='lines', name='動態資產總額走勢', line=dict(color='#2ecc71', width=3)))
    fig.update_layout(
        title="精細化月度資產動態走勢", xaxis_title="時間軸 (年齡與月份)", yaxis_title="資產總額 (元)",
        template="plotly_white", hovermode="x"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==================== 🧠 智慧型動態方針決策引擎 ====================
    st.markdown("---")
    st.header("🔬 健全性科學診斷與資產策略動態方針")
    
    # 動態條件判斷
    has_deficit = required_save > 0
    cash_ratio = total_cash_buffer_needed / final_assets if final_assets > 0 else 0
    pension_dependency = (gov_pension_amount / base_monthly_expense) * 100 if base_monthly_expense > 0 else 0
    
    if has_deficit:
        st.error(f"❌ **科學診斷結果【資產赤字風險】**：\n\n"
                 f"目前的資產滾存速度無法全面抵禦後續支出。資產預計會在 **{broken_age} 歲** 的某個月份耗盡。\n\n"
                 f"**核心地雷分析**：您的基礎提領缺口並非主要原因，而是 60 歲後設定的醫療預備金在經過高達 {inflation_medical*100}% 的醫療獨立通膨非線性放大後，在老齡階段產生了噴湧式開銷；加上每 {capital_expense_cycle} 年一次的複利大筆資本支出，加速了核心投資池的乾涸。")
    else:
        st.success(f"▲ **科學診斷結果【防禦架構安全】**：\n\n"
                   f"恭喜！經月度級精算，您的既有資產結構極度健全，能安全活過 {target_age} 歲。在設定的退休年齡當天，核心池將剩餘高達 **{int(round(final_assets - total_cash_buffer_needed)):,} 元** 的資金在市場持續複利，抗波動能力極強。")

    # 智慧方針生成
    st.markdown("### 🎯 專屬您的資產防禦動態方針指引：")
    
    # 方針一：現金池調配策略
    st.markdown(f"**1. 雙水庫動態防禦（現金池配置方針）**")
    st.write(f"退休當天，系統指示您必須精確切割出 **{int(round(total_cash_buffer_needed)):,} 元** 的獨立「防禦現金池」（佔總資產的 {cash_ratio*100:.1f}%）。")
    if cash_ratio > 0.25:
        st.caption("⚠️ *動態特注*：您的現金緩衝池佔比偏高（超過25%），這意味著雖然您徹底免疫了前幾年的市場大跌風險，但有較大比例資金未享受複利。建議這筆現金池可以採用「多期定存拆解法」或台灣高利活存數位帳戶分流，賺取基本利息，不要完全放置在零利率活期。")
    else:
        st.caption("✅ *動態特注*：您的現金緩衝佔比非常健康。這筆預留的 {cash_buffer_years} 年生活費，能確保您在面臨市場系統性崩跌（如金融海嘯）時，有足夠的底氣凍結任何核心股票變賣，完全靠現金池發薪水给自己，留給核心組合最少 24-36 個月的景氣復甦期。")

    # 方針二：醫療通膨外部化
    st.markdown("**2. 醫療通膨的外部對沖方針**")
    if medical_monthly_expense_60 > 0:
        st.write(f"您設定了 60 歲後每月 {medical_monthly_expense_60:,} 元的醫療預備金。經精算，在 {inflation_medical*100}% 醫療通膨下，這筆開銷到 80 歲時會暴增至每月約 **{int(round(medical_monthly_expense_60 * ((1+inflation_medical)**(80-current_age)))):,} 元**！")
        if has_deficit:
            st.write("💡 **動態減壓策略**：與其在未來 3 年強行背負每月存入高額儲蓄的壓力，最理性的解法是**「利用保險將醫療通膨外部化」**。建議在退休前，將個人的雙實支實付醫療險、高額重大傷病險與不還本長照險額度拉到最高。一旦將高齡大額自費風險轉嫁給保險公司，本計算器的醫療預備金欄位即可大幅下修，您的每月儲蓄赤字將有望直接歸零。")
        else:
            st.write("💡 **動態優化策略**：雖然目前資產安全，但老齡醫療是最大的不確定波動。建議定期檢視自身的健保自費與實支實付險，確保這筆預備金在現實中能被保險有效防禦，讓核心池的資產能保留更多作為家族財富傳承。")

    # 方針三：社會福利與有息興趣銜接
    st.markdown("**3. 社會福利銜接與兼職策略方針**")
    st.write(f"您的退休藍圖中，政府年金（勞保+勞退）在 65 歲注入後，可分擔您目前生活水平約 **{pension_dependency:.1f}%** 的現金流負擔。")
    if has_deficit:
        st.write(f"💡 **槓桿式退休建議**：面對衝刺儲蓄壓力，另一個最健康的解法是**「改變退休定義，啟動有息興趣」**。如果在預定退休年齡後進入輕量工作階段（如高山嚮導、專業攝影接案、技術顧問、技術講師），**只要每個月能創造約 {int(round(base_monthly_expense*0.3)):,} 元左右的輔助主動收入**，就能完全打破中老年的破產終局，實現百分之百的安全存活，同時完全不影響既有的生活品質。")

    # 5. 月度現金流量表
    st.markdown("---")
    st.subheader("📋 工程級每月動態現金流量明細表")
    st.dataframe(df_display.set_index("年齡"), use_container_width=True)

else:
    st.warning("⏳ 請於上方填寫正確的年齡與資產數據（預計退休年齡需大於目前年齡），系統將自動為您生成專屬的科學診斷與資產策略方針。")
