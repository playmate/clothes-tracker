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

st.title("📦 Clothes Tracker")

@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        st.error("Hittar inte filen: data/clothes.xlsx")
        st.stop()

    df = pd.read_excel(DATA_PATH)

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )

    df = df.rename(columns={
        "color": "colour",
        "price_yuan": "price_yuan",
        "price_yuan_": "price_yuan",
        "price_yuan": "price_yuan",
        "weight": "weight_g",
        "weight_in_wh": "weight_g",
    })

    if "price_yuan" not in df.columns and "price_yuan" in df.columns:
        df["price_yuan"] = df["price_yuan"]

    if "price_yuan" in df.columns:
        df["price_yuan"] = (
            df["price_yuan"]
            .astype(str)
            .str.replace("¥", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace("nan", "", regex=False)
            .str.strip()
        )
        df["price_yuan"] = pd.to_numeric(df["price_yuan"], errors="coerce")

    if "weight_g" in df.columns:
        df["weight_g"] = (
            df["weight_g"]
            .astype(str)
            .str.replace("g", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("nan", "", regex=False)
            .str.strip()
        )
        df["weight_g"] = pd.to_numeric(df["weight_g"], errors="coerce")

    return df


df = load_data()

for col in [
    "status",
    "brand",
    "type",
    "size",
    "colour",
    "price_yuan",
    "weight_g",
    "yupoo",
    "qc",
    "pic",
]:
    if col not in df.columns:
        df[col] = ""

st.sidebar.header("Filter")

cny_to_sek = st.sidebar.number_input(
    "CNY → SEK kurs",
    min_value=0.0,
    value=1.45,
    step=0.01
)

df["price_sek"] = df["price_yuan"] * cny_to_sek

search = st.sidebar.text_input("Sök", "")

status_options = sorted(df["status"].dropna().astype(str).unique())
brand_options = sorted(df["brand"].dropna().astype(str).unique())
type_options = sorted(df["type"].dropna().astype(str).unique())

selected_status = st.sidebar.multiselect(
    "Status",
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

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Items", len(filtered))
col2.metric("Total yuan", f"¥{filtered['price_yuan'].sum(skipna=True):,.0f}")
col3.metric("Total SEK", f"{filtered['price_sek'].sum(skipna=True):,.0f} kr")
col4.metric("Total weight", f"{filtered['weight_g'].sum(skipna=True) / 1000:.2f} kg")
col5.metric("Brands", filtered["brand"].nunique())

st.divider()

st.subheader("Alla plagg")

show_cols = [
    "status",
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
    filtered[show_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "status": "Status",
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
            text="count"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen data att visa.")

with right:
    st.subheader("Status")

    status_count = filtered["status"].value_counts().reset_index()
    status_count.columns = ["status", "count"]

    if not status_count.empty:
        fig = px.pie(
            status_count,
            names="status",
            values="count"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen data att visa.")

st.divider()

st.subheader("Detaljer")

if filtered.empty:
    st.warning("Inga plagg matchar filtret.")
else:
    filtered = filtered.reset_index(drop=True)

    labels = (
        filtered["brand"].astype(str)
        + " – "
        + filtered["type"].astype(str)
        + " – "
        + filtered["colour"].astype(str)
        + " – "
        + filtered["status"].astype(str)
    )

    selected_label = st.selectbox("Välj plagg", labels)
    selected_index = labels[labels == selected_label].index[0]
    item = filtered.loc[selected_index]

    c1, c2 = st.columns(2)

    with c1:
        st.write(f"**Status:** {item['status']}")
        st.write(f"**Brand:** {item['brand']}")
        st.write(f"**Type:** {item['type']}")
        st.write(f"**Size:** {item['size']}")
        st.write(f"**Colour:** {item['colour']}")

    with c2:
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
