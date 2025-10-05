# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib
import matplotlib.pyplot as plt

# ✅ 设置中文字体，避免乱码（Mac 用户推荐使用 PingFang SC）
matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False  # 正常显示负号

# === 数据加载 ===
@st.cache_data
def load_data(file_name):
    folder_path = '/Users/elaine_pro/Dropbox/RawData/AIVL_FM/prod_rank_0615/6.5_panel_labeled_MergeDetaildata_sales'
    file_path = os.path.join(folder_path, file_name)
    df = pd.read_csv(file_path, low_memory=False)
    return df

# === 获取所有可选文件 ===
folder_path = '/Users/elaine_pro/Dropbox/RawData/AIVL_FM/prod_rank_0615/6.5_panel_labeled_MergeDetaildata_sales'
all_files = sorted([f for f in os.listdir(folder_path) if f.startswith("panel_TH_") and f.endswith(".csv")])

# === 页面结构 ===
st.title("📊 Product Performance Volatility Dashboard")
st.markdown("探索不同类目产品在时间维度上的绩效波动与结构变化。")

# === 侧边栏：选择文件 + 时间筛选 ===
st.sidebar.header("📂 数据文件与筛选")
selected_file = st.sidebar.selectbox("选择一个类目文件：", all_files)
df = load_data(selected_file)

# === 基础映射 ===
mapping = {'non': 0, 'low': 1, 'middle': 2, 'high': 3, 'top': 4}
df['performance_score'] = df['performance_label'].map(mapping)

# === 时间顺序 ===
dates_sorted = sorted(df['date_value'].unique().tolist())

# 时间筛选器
start_date = st.sidebar.selectbox("选择起始周", dates_sorted, index=0)
end_date = st.sidebar.selectbox("选择结束周", dates_sorted, index=len(dates_sorted)-1)
start_idx, end_idx = dates_sorted.index(start_date), dates_sorted.index(end_date)
selected_range = dates_sorted[start_idx:end_idx + 1]
df = df[df['date_value'].isin(selected_range)]

st.markdown(f"### 当前数据文件：**{selected_file}**")
st.markdown(f"### 当前时间范围：**{start_date} → {end_date}**")

# === 模块 1：整体概览指标（仅纳入在周期内至少出现过一次 low/middle/high/top 的产品） ===
st.subheader("① 整体概览指标（过滤后）")

valid_levels = ['low', 'middle', 'high', 'top']

# 找出在当前时间区间内至少出现过一次有效绩效的产品
eligible_products = df.loc[df['performance_label'].isin(valid_levels), 'product_id'].unique()

if len(eligible_products) == 0:
    st.warning("所选时间段内没有符合条件的产品（至少一次为 low/middle/high/top）。")
else:
    # 仅保留这些产品
    df_filtered = df[df['product_id'].isin(eligible_products)].copy()

    # 计算绩效波动强度（标准差）
    volatility = (
        df_filtered.groupby('product_id')['performance_score']
        .std()
        .reset_index(name='performance_std')
        .dropna(subset=['performance_std'])
    )

    # === 三项核心指标 ===
    col1, col2, col3 = st.columns(3)
    col1.metric("平均波动强度 (Std)", f"{volatility['performance_std'].mean():.2f}")
    col2.metric("纳入产品数量", f"{len(volatility):,}")
    col3.metric("时间区间长度", f"{len(selected_range)} 周")

    # === 补充说明 ===
    st.caption(
        "本模块仅统计在所选时间范围内**至少出现过一次 low/middle/high/top** 的产品。"
        "波动强度衡量产品绩效的时间波动幅度，越大表示波动越剧烈。"
    )

st.markdown("---")

# === 模块 2：整体绩效结构变化趋势（保留 'non'，固定样本基准） ===
st.subheader("② 整体绩效结构变化趋势（含 non 状态）")

valid_levels = ['low', 'middle', 'high', 'top']

# 1️⃣ 找出在整个周期内至少出现过一次有效绩效的产品
eligible_products = df.loc[df['performance_label'].isin(valid_levels), 'product_id'].unique()
total_products = len(eligible_products)

if total_products == 0:
    st.warning("所选时间段内没有符合条件的产品（至少一次为 low/middle/high/top）。")
else:
    # 2️⃣ 过滤这些产品
    df_filtered = df[df['product_id'].isin(eligible_products)].copy()

    # 3️⃣ 每周每等级的产品数
    weekly_trend = (
        df_filtered.groupby(['date_value', 'performance_label'])['product_id']
        .nunique()
        .reset_index(name='count')
    )

    # 4️⃣ 每周比例：用固定样本数 total_products 作分母
    weekly_trend['ratio'] = weekly_trend['count'] / total_products

    # 5️⃣ 转为绘图透视表
    pivot = weekly_trend.pivot(index='date_value', columns='performance_label', values='ratio').fillna(0)
    for label in ['non','low','middle','high','top']:
        if label not in pivot.columns:
            pivot[label] = 0
    pivot = pivot.reindex(selected_range)

    # 6️⃣ 绘制堆积图（保留 non）
    fig, ax = plt.subplots(figsize=(10,5))
    pivot[['non','low','middle','high','top']].plot(kind='area', stacked=True, colormap='tab10', ax=ax)
    ax.set_title('Performance Composition Over Time (Including non)')
    ax.set_ylabel('Proportion of Eligible Products')
    ax.set_xlabel('Date (Week)')
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # 7️⃣ 额外统计信息
    avg_products_per_week = df_filtered.groupby('date_value')['product_id'].nunique().mean()
    st.markdown(f"""
    **总样本数（固定）：** {total_products:,}  
    **平均每周有绩效记录的产品数：** {avg_products_per_week:.1f}  
    （纳入样本：在整个周期中至少出现一次 *low/middle/high/top* 的产品；
    图中比例基于固定样本池计算，包含 'non' 状态）
    """)


# === 模块 3：市场波动强度分布（仅纳入在所选区间内至少出现过一次 low/middle/high/top 的产品） ===
st.subheader("③ 市场波动强度分布（过滤后）")

valid_levels = ['low', 'middle', 'high', 'top']

# 找到在本时间段内至少出现过一次非 non 等级的产品
eligible_products = df.loc[df['performance_label'].isin(valid_levels), 'product_id'].unique()

if len(eligible_products) == 0:
    st.warning("所选时间段内没有满足条件的产品（至少一次为 low/middle/high/top）。")
else:
    # 过滤数据，只保留这些产品
    df_filtered = df[df['product_id'].isin(eligible_products)].copy()

    # 重新计算波动强度（标准差）
    volatility_filtered = (
        df_filtered.groupby('product_id')['performance_score']
        .std()
        .reset_index(name='performance_std')
        .dropna(subset=['performance_std'])
    )

    # 绘制波动强度分布图
    fig, ax = plt.subplots(figsize=(7,4))
    sns.histplot(volatility_filtered['performance_std'], bins=20, kde=True, color='skyblue', ax=ax)
    ax.set_title('Distribution of Performance Volatility (Filtered by Eligible Products)')
    ax.set_xlabel('Performance Std (Volatility)')
    ax.set_ylabel('Number of Products')
    st.pyplot(fig)

    # 显示统计信息
    st.caption(
        f"纳入产品数：{len(volatility_filtered):,} "
        f"（仅包含在当前时间区间内至少出现一次 low/middle/high/top 的产品）"
    )

    # === 🧠 图表解读 ===
    st.markdown("""
    **图表说明：**
    - 本图展示了各产品在所选时间段内的 **绩效波动强度（标准差）分布**。
    - **横轴（Performance Std）** 表示绩效波动幅度：  
      - 数值越低（靠左） → 产品绩效越稳定；  
      - 数值越高（靠右） → 产品绩效波动越大。
    - **纵轴（Number of Products）** 表示处于对应波动区间的产品数量。
    - 曲线越陡 → 市场整体稳定性越高；  
      曲线越平、右尾越长 → 表示市场中存在较多“绩效起伏大”的产品。
    - 可以结合类目或时间范围来观察：  
      - 若多数产品集中在低波动区间（靠左），说明市场稳定、竞争格局清晰；  
      - 若分布向右偏，说明市场活跃或波动剧烈，可能存在爆品与衰退品并存的现象。
    """)

# === 模块 4：单个产品相对上周期的绩效变化（Δ） ===
st.subheader("④ 单个产品相对上周期的绩效变化（Δ）")
product_list = sorted(df['product_id'].unique())
selected_product = st.selectbox("选择一个产品查看绩效变化：", product_list)

sub = df[df['product_id'] == selected_product].copy()
sub['date_cat'] = pd.Categorical(sub['date_value'], categories=selected_range, ordered=True)
sub = sub.sort_values('date_cat')
sub['delta'] = sub['performance_score'].diff()
change_df = sub.dropna(subset=['delta']).copy()
bar_colors = change_df['delta'].apply(
    lambda d: 'tab:green' if d > 0 else ('tab:red' if d < 0 else 'tab:gray')
)
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(change_df['date_value'], change_df['delta'], color=bar_colors)
ax.axhline(0, color='black', linewidth=1, alpha=0.5)
ax.set_ylabel('Δ Performance (等级变化)')
ax.set_xlabel('Date (Week)')
ax.set_title(f'WoW Change vs Previous Period - Product {selected_product}')
plt.xticks(rotation=45)
st.pyplot(fig)
up_cnt = (change_df['delta'] > 0).sum()
down_cnt = (change_df['delta'] < 0).sum()
flat_cnt = (change_df['delta'] == 0).sum()
st.caption(f"变化统计：上升 {up_cnt} 次，下降 {down_cnt} 次，持平 {flat_cnt} 次。")

# === 模块 5：产品绩效阶段表 ===
st.subheader("⑤ 产品绩效阶段变化")
def find_periods(x, cats):
    x = x.copy()
    x['date_cat'] = pd.Categorical(x['date_value'], categories=cats, ordered=True)
    x = x.sort_values('date_cat').reset_index(drop=True)
    x['change_flag'] = (x['performance_label'] != x['performance_label'].shift()).cumsum()
    return (
        x.groupby('change_flag')
         .agg(
             performance_label=('performance_label', 'first'),
             start_date=('date_value', 'first'),
             end_date=('date_value', 'last'),
             duration=('date_value', 'count')
         )
         .reset_index(drop=True)
    )
periods = find_periods(sub, selected_range)
st.dataframe(periods)

# === 模块 6：单个产品绩效变化趋势（折线图，无标签） ===
st.subheader("⑥ 单个产品绩效变化趋势（折线图）")
perf_seq = sub[['date_value', 'performance_score', 'performance_label']].copy()
perf_seq['date_cat'] = pd.Categorical(perf_seq['date_value'], categories=selected_range, ordered=True)
perf_seq = perf_seq.sort_values('date_cat')
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(
    perf_seq['date_value'],
    perf_seq['performance_score'],
    marker='o',
    linewidth=2,
    color='steelblue'
)
ax.set_ylim(-0.5, 4.5)
ax.set_yticks([0, 1, 2, 3, 4])
ax.set_yticklabels(['non', 'low', 'middle', 'high', 'top'])
ax.set_xlabel('Date (Week)')
ax.set_ylabel('Performance Level')
ax.set_title(f'Performance Changes Over Time - Product {selected_product}')
plt.xticks(rotation=45)
st.pyplot(fig)