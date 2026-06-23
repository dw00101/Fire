import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 網頁與手機版畫面最佳化設定
st.set_page_config(page_title="我的退休計劃計算器", layout="centered")

st.title("📊 我的退休計劃計算器")
st.write("調整下方參數，即時計算專屬的退休現金流量表。")

st.markdown("---")

# --- 側邊欄 / 參數輸入區 (對應手機版會折疊或置頂) ---
st.header("⚙️ 投資與基本資訊設定")

col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input("目前年齡", min_value=0, max_value=100, value=37, step=1)
    retire_age = st.number_input("預計退休年齡", min_value=current_age, max_value=100, value=40, step=1)
    target_age = st.number_input("退休金希望夠用到幾歲", min_value=retire_age, max_value=110, value=100, step=1)

with col2:
    current_assets = st.number_input("目前資產總額 (元)", min_value=0, value=48000000, step=1000000, format="%d")
    monthly_withdrawal = st.number_input("剛退休的每月提領額 (元)", min_value=0, value=166667, step=5000, format="%d")
    monthly_deposit = st.number_input("退休前，每月底存入金額 (元)", min_value=0, value=0, step=1000)

# 滑桿設定報酬率與通膨
roi = st.slider("預期年化投資報酬率 (%)", min_value=0.0, max_value=15.0, value=6.0, step=0.5) / 100
inflation = st.slider("預期通貨膨脹率 (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1) / 100

st.markdown("---")

# --- 核心邏輯計算 ---
years_to_retire = retire_age - current_age
retirement_years = target_age - retire_age

# 1. 計算退休衝刺期的資產累積 (37歲到40歲)
assets = current_assets
for year in range(years_to_retire):
    # 假設年底結算：本金滾利 + 全年累積儲蓄
    assets = (assets * (1 + roi)) + (monthly_deposit * 12)

assets_at_retirement = assets
annual_withdrawal_first_year = monthly_withdrawal * 12

# 2. 模擬退休後的現金流歷程
age_list = []
asset_list = []
withdrawal_list = []
roi_list = []

current_retire_assets = assets_at_retirement
current_annual_withdrawal = annual_withdrawal_first_year

for year in range(retirement_years + 1):
    current_age_loop = retire_age + year
    age_list.append(current_age_loop)
    asset_list.append(current_retire_assets)
    withdrawal_list.append(current_annual_withdrawal)
    
    # 計算當年的投資收益並結算至期末
    roi_earnings = (current_retire_assets - current_annual_withdrawal) * roi
    roi_list.append(roi_earnings)
    
    # 期末資產
    current_retire_assets = current_retire_assets - current_annual_withdrawal + roi_earnings
    # 下一年的提領額隨通膨調整
    current_annual_withdrawal = current_annual_withdrawal * (1 + inflation)

# 建立 DataFrame 方便呈現
df_cashflow = pd.DataFrame({
    "年齡": age_list,
    "期初資產": asset_list,
    "該年每月提領": [w / 12 for w in withdrawal_list],
    "年度總支出": withdrawal_list,
    "預期投資收益": roi_list
})
df_cashflow["期末資產"] = df_cashflow["期初資產"] - df_cashflow["年度總支出"] + df_cashflow["預期投資收益"]

# --- 畫面結果呈現 ---
st.subheader("🎉 計算結果")

metric_col1, metric_col2 = st.columns(2)
metric_col1.metric("退休時總資產估算", f"{assets_at_retirement:,.0f} 元")
metric_col2.metric("第一年預計年提領", f"{annual_withdrawal_first_year:,.0f} 元")

# 繪製資產走勢圖 (使用 Plotly 支援手機動態縮放與手指滑動查看)
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_cashflow["年齡"], y=df_cashflow["期初資產"], mode='lines', name='資產總額', line=dict(color='#1f77b4', width=3)))
fig.update_layout(
    title="退休後資產總額隨時間變化趨勢",
    xaxis_title="年齡",
    yaxis_title="資產總額 (元)",
    template="plotly_white",
    hovermode="x"
)
st.plotly_chart(fig, use_container_width=True)

# 顯示現金流量表
st.subheader("📋 每月/每年度詳細現金流量表")
st.write("（可自由上下滑動、雙指放大查看明細）")

# 格式化表格內容輸出
df_display = df_cashflow.copy()
df_display["期初資產"] = df_display["期初資產"].map('{:,.0f} 元'.format)
df_display["該年每月提領"] = df_display["該年每月提領"].map('{:,.0f} 元'.format)
df_display["年度總支出"] = df_display["年度總支出"].map('{:,.0f} 元'.format)
df_display["預期投資收益"] = df_display["預期投資收益"].map('{:,.0f} 元'.format)
df_display["期末資產"] = df_display["期末資產"].map('{:,.0f} 元'.format)

st.dataframe(df_display.set_index("年齡"), use_container_width=True)

st.caption("註：本計算器之試算結果僅供財務規劃參考，實際資產走勢仍受市場實質波動影響。")
