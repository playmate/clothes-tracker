import os
from io import BytesIO
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import plotly.express as px


# =========================
# APP CONFIG
# =========================
st.set_page_config(
    page_title="Clothing Orders",
    page_icon="🧥",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = "data/clothes.xlsx"

STATUS_ORDER = [
    "purchased",
    "shipped locally",
    "warehouse",
    "shipped internationally",
    "delivered",
]

STATUS_COLORS = {
    "purchased": "#7C3AED",
    "shipped locally": "#2563EB",
    "warehouse": "#F59E0B",
    "shipped internationally": "#06B6D4",
    "delivered": "#22C55E",
}

REQUIRED_COLUMNS = [
    "item",
    "brand",
    "type",
    "status",
    "yuan",
    "sek",
    "weight",
    "yupoo",
    "qc",
]


# =========================
# STYLING
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(80, 80, 120, 0.22), transparent 32%),
            linear-gradient(180deg, #050505 0%, #0b0b0f 45%, #111114 100%);
        color: #f5f5f7;
    }

    section[data-testid="stSidebar"] {
        background: rgba(20, 20, 24, 0.72);
        backdrop-filter: blur(22px);
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    h1, h2, h3 {
        letter-spacing: -0.04em;
    }

    .hero {
        padding: 28px 30px;
        border-radius: 32px;
        background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03));
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: 0 25px 80px rgba(0,0,0,0.35);
        margin-bottom: 24px;
    }

    .hero-title {
        font-size: 44px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .hero-subtitle {
        color: rgba(245,245,247,0.68);
        font-size: 17px;
    }

    .metric-card {
        padding: 22px;
        border-radius: 26px;
        background: rgba(255,255,255,0.075);
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 16px 50px rgba(0,0,0,0.24);
    }

    .metric-label {
        color: rgba(245,245,247,0.58);
        font-size: 13px;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 30px;
        font-weight: 760;
        letter-spacing: -0.04em;
    }

    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 24px;
        overflow: hidden;
    }

    .small-muted {
        color: rgba(245,245,247,0.55);
        font-size: 13px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.075);
        color: #f5f5f7;
        padding: 0.75rem 1rem;
        font-weight: 650;
    }

    .stButton > button:hover {
        border-color: rgba(255,255,255,0.35);
        background: rgba(255,255,255,0.12);
        color: white;
    }

    @media (max-width: 768px) {
        .hero-title {
            font-size: 32px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# HELPERS
# =========================
def get_data_source() -> str:
    try:
        if "onedrive_excel_url" in st.secrets:
            return st.secrets["onedrive_excel_url"]
    except Exception:
        pass

    env_url = os.getenv("ONEDRIVE_EXCEL_URL")
    if env_url:
        return env_url

    return DATA_PATH


@st.cache_data(ttl=3600)
def get_cny_to_sek_rate() -> float:
    try:
        url = "https://api.frankfurter.app/latest?from=CNY&to=SEK"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
        return float(data["rates"]["SEK"])
    except Exception:
        return 1.45


@st.cache_data(ttl=120)
def load_data(source: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(source, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)

    df.columns = [str(c).strip().lower() for c in df.columns]

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[REQUIRED_COLUMNS].copy()

    df["status"] = (
        df["status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"nan": "purchased", "": "purchased"})
    )

    df.loc[~df["status"].isin(STATUS_ORDER), "status"] = "purchased"

    df["yuan"] = pd.to_numeric(df["yuan"], errors="coerce").fillna(0)
    df["sek"] = pd.to_numeric(df["sek"], errors="coerce").fillna(0)
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0)

    for col in ["item", "brand", "type", "yupoo", "qc"]:
        df[col] = df[col].fillna("").astype(str)

    return df


def add_calculated_columns(df: pd.DataFrame, rate: float) -> pd.DataFrame:
    df = df.copy()

    missing_sek = df["sek"].isna() | (df["sek"] == 0)
    df.loc[missing_sek, "sek"] = df.loc[missing_sek, "yuan"] * rate

    df["status_rank"] = df["status"].apply(lambda x: STATUS_ORDER.index(x))
    df = df.sort_values(["status_rank", "brand", "item"]).drop(columns=["status_rank"])

    return df


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()

    export_df = df[REQUIRED_COLUMNS].copy()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="clothes")

    return output.getvalue()


def render_metric(label: str, value: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_link(value: str) -> str:
    value = str(value).strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return ""


# =========================
# LOAD DATA
# =========================
source = get_data_source()
rate = get_cny_to_sek_rate()
raw_df = load_data(source)
df = add_calculated_columns(raw_df, rate)


# =========================
# HEADER
# =========================
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">Clothing Orders</div>
        <div class="hero-subtitle">
            Track reps, shipping status, costs, weight, Yupoo links and QC links.
            Current CNY → SEK rate: <b>{rate:.3f}</b>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.title("Filters")

search = st.sidebar.text_input("Search", placeholder="Search item, brand, type...")

brands = sorted([x for x in df["brand"].dropna().unique() if str(x).strip()])
types = sorted([x for x in df["type"].dropna().unique() if str(x).strip()])

selected_brands = st.sidebar.multiselect("Brand", brands)
selected_types = st.sidebar.multiselect("Type", types)
selected_statuses = st.sidebar.multiselect("Status", STATUS_ORDER)

if "status_card_filter" not in st.session_state:
    st.session_state.status_card_filter = []

if st.sidebar.button("Clear all filters"):
    st.session_state.status_card_filter = []
    st.rerun()


# =========================
# CLICKABLE STATUS CARDS
# =========================
st.subheader("Status overview")

status_cols = st.columns(len(STATUS_ORDER))

for i, status in enumerate(STATUS_ORDER):
    count = int((df["status"] == status).sum())
    yuan_sum = float(df.loc[df["status"] == status, "yuan"].sum())

    with status_cols[i]:
        label = f"{status.title()}\n\n{count} items · ¥{yuan_sum:,.0f}"
        if st.button(label, key=f"status_card_{status}"):
            if status in st.session_state.status_card_filter:
                st.session_state.status_card_filter.remove(status)
            else:
                st.session_state.status_card_filter = [status]
            st.rerun()


# =========================
# APPLY FILTERS
# =========================
filtered = df.copy()

active_statuses = selected_statuses or st.session_state.status_card_filter

if search:
    mask = (
        filtered["item"].str.contains(search, case=False, na=False)
        | filtered["brand"].str.contains(search, case=False, na=False)
        | filtered["type"].str.contains(search, case=False, na=False)
        | filtered["status"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

if selected_brands:
    filtered = filtered[filtered["brand"].isin(selected_brands)]

if selected_types:
    filtered = filtered[filtered["type"].isin(selected_types)]

if active_statuses:
    filtered = filtered[filtered["status"].isin(active_statuses)]


# =========================
# METRICS
# =========================
st.subheader("Summary")

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    render_metric("Total items", f"{len(filtered)}")

with m2:
    render_metric("Total yuan", f"¥{filtered['yuan'].sum():,.0f}")

with m3:
    render_metric("Total SEK", f"{filtered['sek'].sum():,.0f} kr")

with m4:
    render_metric("Total weight", f"{filtered['weight'].sum():,.2f} kg")

with m5:
    render_metric("Brand count", f"{filtered['brand'].replace('', pd.NA).dropna().nunique()}")


# =========================
# CHARTS
# =========================
st.subheader("Charts")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    brand_data = (
        filtered[filtered["brand"].str.strip() != ""]
        .groupby("brand", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )

    if not brand_data.empty:
        fig = px.bar(
            brand_data,
            x="brand",
            y="count",
            title="Brand chart",
            template="plotly_dark",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f5f5f7",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No brand data available.")

with chart_col2:
    status_data = (
        filtered.groupby("status", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    status_data["status"] = pd.Categorical(
        status_data["status"],
        categories=STATUS_ORDER,
        ordered=True,
    )
    status_data = status_data.sort_values("status")

    if not status_data.empty:
        fig = px.bar(
            status_data,
            x="status",
            y="count",
            title="Status chart",
            color="status",
            color_discrete_map=STATUS_COLORS,
            template="plotly_dark",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f5f5f7",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No status data available.")

weight_data = filtered.copy()
weight_data = weight_data[weight_data["weight"] > 0]

if not weight_data.empty:
    fig = px.bar(
        weight_data,
        x="item",
        y="weight",
        color="status",
        color_discrete_map=STATUS_COLORS,
        title="Weight chart",
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f5f5f7",
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================
# TABLE
# =========================
st.subheader("Orders")

display_df = filtered.copy()

display_df["yupoo"] = display_df["yupoo"].apply(clean_link)
display_df["qc"] = display_df["qc"].apply(clean_link)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "item": st.column_config.TextColumn("Item"),
        "brand": st.column_config.TextColumn("Brand"),
        "type": st.column_config.TextColumn("Type"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=STATUS_ORDER,
        ),
        "yuan": st.column_config.NumberColumn("Yuan", format="¥%.0f"),
        "sek": st.column_config.NumberColumn("SEK", format="%.0f kr"),
        "weight": st.column_config.NumberColumn("Weight", format="%.2f kg"),
        "yupoo": st.column_config.LinkColumn("Yupoo"),
        "qc": st.column_config.LinkColumn("QC"),
    },
)


# =========================
# EDITOR
# =========================
st.subheader("Edit data")

st.markdown(
    """
    <div class="small-muted">
    Edit your orders here, then download the updated Excel file.
    Upload it back to GitHub or OneDrive through the browser.
    </div>
    """,
    unsafe_allow_html=True,
)

edited_df = st.data_editor(
    df[REQUIRED_COLUMNS],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=STATUS_ORDER,
            required=True,
        ),
        "yuan": st.column_config.NumberColumn("Yuan", min_value=0),
        "sek": st.column_config.NumberColumn("SEK", min_value=0),
        "weight": st.column_config.NumberColumn("Weight", min_value=0),
        "yupoo": st.column_config.LinkColumn("Yupoo"),
        "qc": st.column_config.LinkColumn("QC"),
    },
)

excel_bytes = to_excel_bytes(edited_df)

st.download_button(
    label="Download updated Excel",
    data=excel_bytes,
    file_name="clothes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)


# =========================
# DATA SOURCE INFO
# =========================
with st.expander("Data source"):
    st.write("Current source:")
    st.code(str(source))

    st.write("For OneDrive read-only mode, add this to Streamlit secrets:")
    st.code('onedrive_excel_url = "YOUR_ONEDRIVE_DIRECT_DOWNLOAD_LINK"')

    st.write("Last refreshed:")
    st.code(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
