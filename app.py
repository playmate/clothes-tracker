import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Clothes Tracker",
    page_icon="📦",
    layout="wide"
)

DATA_PATH = Path("data/clothes.xlsx")

STATUS_ORDER = [
    "purchased",
    "shipped locally",
    "warehouse",
    "shipped internationally",
    "delivered",
]

STATUS_COLORS = {
    "purchased": "#ef4444",
    "shipped locally": "#f97316",
    "warehouse": "#eab308",
    "shipped internationally": "#3b82f6",
    "delivered": "#22c55e",
}

STATUS_LABELS = {
    "purchased": "Purchased",
    "shipped locally": "Shipped locally",
    "warehouse": "Warehouse",
    "shipped internationally": "Shipped internationally",
    "delivered": "Delivered",
}

st.markdown("""
<style>
.main {
    background: #0f1117;
}

.block-container {
    padding-top: 2rem;
}

.hero {
    padding: 26px 30px;
    border-radius: 26px;
    background: linear-gradient(135deg, #171923 0%, #222736 100%);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 24px;
}

.hero h1 {
    font-size: 42px;
    margin: 0;
}

.hero p {
    color: #a1a1aa;
    font-size: 16px;
    margin-top: 8px;
}

.metric-card {
    padding: 22px;
    border-radius: 22px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
}

.metric-label {
    color: #a1a1aa;
    font-size: 14px;
}

.metric-value {
    font-size: 30px;
    font-weight: 700;
    margin-top: 4px;
}

.status-pill {
    display: inline-block;
    padding: 6px 11px;
    border-radius: 999px;
    color: white;
    font-size: 13px;
    font-weight: 700;
}

.item-card {
    padding: 18px;
    border-radius: 22px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 14px;
}

.small-muted {
    color: #a1a1aa;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        st.error("Hittar inte filen: data/clothes.xlsx")
        st.stop()

    df = pd.read_excel(DATA_PATH)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )

    df = df.rename(columns={
        "color": "colour",
        "weight": "weight_g",
        "weight_in_wh": "weight_g",
    })

    for col in [
        "status", "brand", "type", "size", "colour",
        "price_yuan", "weight_g", "yupoo", "qc", "pic"
    ]:
        if col not in df.columns:
            df[col] = ""

    df["status"] = df["status"].astype(str).str.strip().str.lower()

    df["status"] = df["status"].replace({
        "shipped": "shipped internationally",
        "international": "shipped internationally",
        "shipped international": "shipped internationally",
        "local": "shipped locally",
    })

    df["price_yuan"] = (
        df["price_yuan"]
        .astype(str)
        .str.replace("¥", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace("nan", "", regex=False)
        .str.strip()
    )
    df["price_yuan"] = pd.to_numeric(df["price_yuan"], errors="coerce")

    df["weight_g"] = (
        df["weight_g"]
        .astype(str)
        .str.replace("g", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("nan", "", regex=False)
        .str.strip()
    )
    df["weight_g"] = pd.to_numeric(df["weight_g"], errors="coerce")

    df["status_rank"] = df["status"].apply(
        lambda x: STATUS_ORDER.index(x) if x in STATUS_ORDER else 999
    )

    df = df.sort_values(["status_rank", "brand", "type"]).reset_index(drop=True)

    return df


df = load_data()

st.markdown("""
<div class="hero">
    <h1>📦 Clothes Tracker</h1>
    <p>Orderöversikt för plagg, vikt, status, QC och kostnad.</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("Filter")

cny_to_sek = st.sidebar.number_input(
    "CNY → SEK kurs",
    min_value=0.0,
    value=1.45,
    step=0.01
)

df["price_sek"] = df["price_yuan"] * cny_to_sek

search = st.sidebar.text_input("Sök", "")

status_options = [s for s in STATUS_ORDER if s in df["status"].unique()]
extra_statuses = sorted([s for s in df["status"].dropna().unique() if s not in STATUS_ORDER])
status_options += extra_statuses

brand_options = sorted(df["brand"].dropna().astype(str).unique())
type_options = sorted(df["type"].dropna().astype(str).unique())

selected_status = st.sidebar.multiselect(
    "Status / Location",
    status_options,
    default=status_options
)

selected_brand = st.sidebar.multiselect(
    "Brand",
    brand_options,
    default=brand_options
)

selected_type = st.sidebar.multiselect(
    "Type",
    type_options,
    default=type_options
)

filtered = df[
    df["status"].astype(str).isin(selected_status)
    & df["brand"].astype(str).isin(selected_brand)
    & df["type"].astype(str).isin(selected_type)
].copy()

if search:
    search_lower = search.lower()
    filtered = filtered[
        filtered.astype(str).apply(
            lambda row: row.str.lower().str.contains(search_lower, na=False).any(),
            axis=1
        )
    ]

filtered = filtered.sort_values(["status_rank", "brand", "type"]).reset_index(drop=True)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Items</div>
        <div class="metric-value">{len(filtered)}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total yuan</div>
        <div class="metric-value">¥{filtered["price_yuan"].sum(skipna=True):,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total SEK</div>
        <div class="metric-value">{filtered["price_sek"].sum(skipna=True):,.0f} kr</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total weight</div>
        <div class="metric-value">{filtered["weight_g"].sum(skipna=True) / 1000:.2f} kg</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Brands</div>
        <div class="metric-value">{filtered["brand"].nunique()}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

st.subheader("Status / Location")

status_summary = (
    filtered.groupby("status", dropna=False)
    .agg(
        items=("status", "count"),
        weight_g=("weight_g", "sum"),
        value_yuan=("price_yuan", "sum"),
        value_sek=("price_sek", "sum"),
        rank=("status_rank", "min"),
    )
    .reset_index()
    .sort_values("rank")
)

cols = st.columns(max(1, len(status_summary)))

for i, row in status_summary.iterrows():
    status = row["status"]
    color = STATUS_COLORS.get(status, "#71717a")
    label = STATUS_LABELS.get(status, status.title())

    with cols[list(status_summary.index).index(i)]:
        st.markdown(f"""
        <div class="item-card">
            <span class="status-pill" style="background:{color};">{label}</span>
            <div style="height:12px;"></div>
            <div><b>{int(row["items"])}</b> items</div>
            <div class="small-muted">{row["weight_g"] / 1000:.2f} kg</div>
            <div class="small-muted">¥{row["value_yuan"]:,.0f} / {row["value_sek"]:,.0f} kr</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

st.subheader("Alla plagg")

display_df = filtered.copy()
display_df["status_label"] = display_df["status"].map(STATUS_LABELS).fillna(display_df["status"])

show_cols = [
    "status_label",
    "brand",
    "type",
    "size",
    "colour",
    "price_yuan",
    "price_sek",
    "weight_g",
    "yupoo",
    "qc",
]

st.dataframe(
    display_df[show_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "status_label": "Status / Location",
        "brand": "Brand",
        "type": "Type",
        "size": "Size",
        "colour": "Colour",
        "yupoo": st.column_config.LinkColumn("Yupoo"),
        "qc": st.column_config.LinkColumn("QC"),
        "price_yuan": st.column_config.NumberColumn("Price ¥", format="¥%.0f"),
        "price_sek": st.column_config.NumberColumn("Price SEK", format="%.0f kr"),
        "weight_g": st.column_config.NumberColumn("Weight", format="%.0f g"),
    }
)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Plagg per märke")
    brand_count = filtered["brand"].value_counts().reset_index()
    brand_count.columns = ["brand", "count"]

    if not brand_count.empty:
        fig = px.bar(
            brand_count,
            x="brand",
            y="count",
            text="count",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen data att visa.")

with right:
    st.subheader("Statusfördelning")
    status_count = (
        filtered.groupby(["status", "status_rank"])
        .size()
        .reset_index(name="count")
        .sort_values("status_rank")
    )

    if not status_count.empty:
        status_count["status_label"] = status_count["status"].map(STATUS_LABELS).fillna(status_count["status"])

        fig = px.pie(
            status_count,
            names="status_label",
            values="count",
            color="status",
            color_discrete_map=STATUS_COLORS,
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen data att visa.")

st.divider()

st.subheader("Viktfördelning")

weight_by_status = (
    filtered.groupby(["status", "status_rank"], dropna=False)["weight_g"]
    .sum()
    .reset_index()
    .sort_values("status_rank")
)

if not weight_by_status.empty:
    weight_by_status["status_label"] = weight_by_status["status"].map(STATUS_LABELS).fillna(weight_by_status["status"])

    fig_weight = px.bar(
        weight_by_status,
        x="status_label",
        y="weight_g",
        text="weight_g",
        color="status",
        color_discrete_map=STATUS_COLORS,
        labels={
            "status_label": "Status / Location",
            "weight_g": "Weight g",
        },
    )
    fig_weight.update_traces(texttemplate="%{text:.0f} g", textposition="outside")
    fig_weight.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig_weight, use_container_width=True)

st.divider()

st.subheader("Detaljer")

if filtered.empty:
    st.warning("Inga plagg matchar filtret.")
else:
    labels = (
        filtered["brand"].astype(str)
        + " – "
        + filtered["type"].astype(str)
        + " – "
        + filtered["colour"].astype(str)
        + " – "
        + filtered["status"].map(STATUS_LABELS).fillna(filtered["status"]).astype(str)
    )

    selected_label = st.selectbox("Välj plagg", labels)
    selected_index = labels[labels == selected_label].index[0]
    item = filtered.loc[selected_index]

    status = item["status"]
    color = STATUS_COLORS.get(status, "#71717a")
    label = STATUS_LABELS.get(status, status.title())

    d1, d2 = st.columns([1.2, 1])

    with d1:
        st.markdown(f"""
        <div class="item-card">
            <span class="status-pill" style="background:{color};">{label}</span>
            <h3 style="margin-top:16px;">{item["brand"]} – {item["type"]}</h3>
            <div class="small-muted">Size: {item["size"]} · Colour: {item["colour"]}</div>
        </div>
        """, unsafe_allow_html=True)

    with d2:
        price_yuan = item["price_yuan"]
        price_sek = item["price_sek"]
        weight = item["weight_g"]

        st.write(f"**Price:** ¥{price_yuan:.0f}" if pd.notna(price_yuan) else "**Price:** -")
        st.write(f"**SEK:** {price_sek:.0f} kr" if pd.notna(price_sek) else "**SEK:** -")
        st.write(f"**Weight:** {weight:.0f} g" if pd.notna(weight) else "**Weight:** -")

        if str(item.get("yupoo", "")).startswith("http"):
            st.link_button("Öppna Yupoo", item["yupoo"])

        if str(item.get("qc", "")).startswith("http"):
            st.link_button("Öppna QC", item["qc"])
