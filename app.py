import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Clothes Tracker",
    page_icon="📦",
    layout="wide"
)

SHEET_TAB = "clothes"

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

COLUMNS = [
    "status",
    "yupoo",
    "pic",
    "brand",
    "type",
    "size",
    "colour",
    "price_yuan",
    "weight_g",
    "qc",
]

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
}

.hero {
    padding: 28px 32px;
    border-radius: 28px;
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 24px;
}

.hero h1 {
    font-size: 44px;
    margin: 0;
}

.hero p {
    color: #d1d5db;
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
    color: #9ca3af;
    font-size: 14px;
}

.metric-value {
    font-size: 30px;
    font-weight: 700;
    margin-top: 4px;
}

.status-pill {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    color: white;
    font-size: 13px;
    font-weight: 700;
}

.status-button-card {
    padding: 16px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.045);
    margin-bottom: 10px;
}

.item-card {
    padding: 18px;
    border-radius: 22px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 14px;
}

.small-muted {
    color: #9ca3af;
    font-size: 13px;
}

table {
    width: 100%;
    border-collapse: collapse;
    border-radius: 18px;
    overflow: hidden;
}

thead tr {
    background: rgba(255,255,255,0.08);
}

th {
    text-align: left !important;
    padding: 12px !important;
    font-weight: 700 !important;
}

td {
    padding: 11px !important;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}

a {
    text-decoration: none;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_worksheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)
    sheet_name = st.secrets["GOOGLE_SHEET_NAME"]

    spreadsheet = client.open(sheet_name)
    worksheet = spreadsheet.worksheet(SHEET_TAB)

    return worksheet


@st.cache_data(ttl=86400)
def get_cny_to_sek_rate():
    try:
        url = "https://api.frankfurter.app/latest?from=CNY&to=SEK"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data["rates"]["SEK"]), data.get("date", "latest")
    except Exception:
        return 1.45, "fallback"


def normalize_data(df):
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
        "price_yuan": "price_yuan",
    })

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS].copy()

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

    return df.sort_values(["status_rank", "brand", "type"]).reset_index(drop=True)


@st.cache_data(ttl=60)
def load_data():
    worksheet = get_worksheet()
    rows = worksheet.get_all_records()

    if not rows:
        return normalize_data(pd.DataFrame(columns=COLUMNS))

    return normalize_data(pd.DataFrame(rows))


def append_item(item):
    worksheet = get_worksheet()

    existing_headers = worksheet.row_values(1)

    if existing_headers != COLUMNS:
        worksheet.clear()
        worksheet.append_row(COLUMNS)

    worksheet.append_row([
        item.get("status", ""),
        item.get("yupoo", ""),
        item.get("pic", ""),
        item.get("brand", ""),
        item.get("type", ""),
        item.get("size", ""),
        item.get("colour", ""),
        item.get("price_yuan", ""),
        item.get("weight_g", ""),
        item.get("qc", ""),
    ])

    st.cache_data.clear()


def status_badge(status):
    color = STATUS_COLORS.get(status, "#71717a")
    label = STATUS_LABELS.get(status, str(status).title())
    return f'<span class="status-pill" style="background:{color};">{label}</span>'


def make_clickable_link(url, label):
    if isinstance(url, str) and url.startswith("http"):
        return f'<a href="{url}" target="_blank">{label}</a>'
    return ""


cny_to_sek, rate_date = get_cny_to_sek_rate()
df = load_data()
df["price_sek"] = df["price_yuan"] * cny_to_sek

st.markdown(f"""
<div class="hero">
    <h1>📦 Clothes Tracker</h1>
    <p>Track clothing orders, location, weight, QC links and total cost.</p>
    <p class="small-muted">CNY → SEK rate: {cny_to_sek:.4f} · Date: {rate_date}</p>
</div>
""", unsafe_allow_html=True)

with st.expander("➕ Add new item", expanded=False):
    with st.form("add_item_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            new_status = st.selectbox("Status", STATUS_ORDER)
            new_brand = st.text_input("Brand")
            new_type = st.text_input("Type")

        with c2:
            new_size = st.text_input("Size")
            new_colour = st.text_input("Colour")
            new_price = st.number_input("Price yuan", min_value=0.0, step=1.0)

        with c3:
            new_weight = st.number_input("Weight g", min_value=0.0, step=10.0)
            new_yupoo = st.text_input("Yupoo link")
            new_qc = st.text_input("QC link")

        new_pic = st.text_input("Image link / filename", placeholder="Optional")

        submitted = st.form_submit_button("Save item")

        if submitted:
            if not new_brand or not new_type:
                st.error("Brand and Type are required.")
            else:
                append_item({
                    "status": new_status,
                    "yupoo": new_yupoo,
                    "pic": new_pic,
                    "brand": new_brand.strip().lower(),
                    "type": new_type.strip().lower(),
                    "size": new_size.strip(),
                    "colour": new_colour.strip().lower(),
                    "price_yuan": new_price,
                    "weight_g": new_weight,
                    "qc": new_qc,
                })
                st.success("Item saved.")
                st.rerun()

st.sidebar.header("Filters")

search = st.sidebar.text_input("Search", "")

status_options = [s for s in STATUS_ORDER if s in df["status"].unique()]
extra_statuses = sorted([s for s in df["status"].dropna().unique() if s not in STATUS_ORDER])
status_options += extra_statuses

st.sidebar.subheader("Quick status filter")

quick_status = st.sidebar.radio(
    "Show",
    ["All"] + [STATUS_LABELS.get(s, s.title()) for s in status_options],
    index=0
)

if quick_status == "All":
    selected_status = status_options
else:
    reverse_labels = {v: k for k, v in STATUS_LABELS.items()}
    selected_status = [reverse_labels.get(quick_status, quick_status.lower())]

brand_options = sorted(df["brand"].dropna().astype(str).unique())
type_options = sorted(df["type"].dropna().astype(str).unique())

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

st.subheader("Status overview")

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
        <div class="status-button-card">
            <span class="status-pill" style="background:{color};">{label}</span>
            <div style="height:12px;"></div>
            <div><b>{int(row["items"])}</b> items</div>
            <div class="small-muted">{row["weight_g"] / 1000:.2f} kg</div>
            <div class="small-muted">¥{row["value_yuan"]:,.0f} / {row["value_sek"]:,.0f} kr</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

st.subheader("Items")

display_df = filtered.copy()

display_df["Status"] = display_df["status"].apply(status_badge)
display_df["Brand"] = display_df["brand"]
display_df["Type"] = display_df["type"]
display_df["Size"] = display_df["size"]
display_df["Colour"] = display_df["colour"]
display_df["Price ¥"] = display_df["price_yuan"].apply(lambda x: f"¥{x:.0f}" if pd.notna(x) else "")
display_df["Price SEK"] = display_df["price_sek"].apply(lambda x: f"{x:.0f} kr" if pd.notna(x) else "")
display_df["Weight"] = display_df["weight_g"].apply(lambda x: f"{x:.0f} g" if pd.notna(x) else "")
display_df["Yupoo"] = display_df["yupoo"].apply(lambda x: make_clickable_link(x, "Yupoo"))
display_df["QC"] = display_df["qc"].apply(lambda x: make_clickable_link(x, "QC"))

show_cols = [
    "Status",
    "Brand",
    "Type",
    "Size",
    "Colour",
    "Price ¥",
    "Price SEK",
    "Weight",
    "Yupoo",
    "QC",
]

st.markdown(
    display_df[show_cols].to_html(
        escape=False,
        index=False
    ),
    unsafe_allow_html=True
)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Items by brand")
    brand_count = filtered["brand"].value_counts().reset_index()
    brand_count.columns = ["Brand", "Count"]

    if not brand_count.empty:
        fig = px.bar(
            brand_count,
            x="Brand",
            y="Count",
            text="Count",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to display.")

with right:
    st.subheader("Status distribution")
    status_count = (
        filtered.groupby(["status", "status_rank"])
        .size()
        .reset_index(name="count")
        .sort_values("status_rank")
    )

    if not status_count.empty:
        status_count["Status"] = status_count["status"].map(STATUS_LABELS).fillna(status_count["status"])

        fig = px.pie(
            status_count,
            names="Status",
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
        st.info("No data to display.")

st.divider()

st.subheader("Weight distribution")

weight_by_status = (
    filtered.groupby(["status", "status_rank"], dropna=False)["weight_g"]
    .sum()
    .reset_index()
    .sort_values("status_rank")
)

if not weight_by_status.empty:
    weight_by_status["Status"] = weight_by_status["status"].map(STATUS_LABELS).fillna(weight_by_status["status"])

    fig_weight = px.bar(
        weight_by_status,
        x="Status",
        y="weight_g",
        text="weight_g",
        color="status",
        color_discrete_map=STATUS_COLORS,
        labels={
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

st.subheader("Details")

if filtered.empty:
    st.warning("No items match the selected filters.")
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

    selected_label = st.selectbox("Select item", labels)
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
            st.link_button("Open Yupoo", item["yupoo"])

        if str(item.get("qc", "")).startswith("http"):
            st.link_button("Open QC", item["qc"])
