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

    # Hantera olika kolumnnamn
    df = df.rename(columns={
        "price_yuan": "price_yuan",
        "price_yuan_": "price_yuan",
        "price_yuan": "price_yuan",
        "price_yuan": "price_yuan",
        "colour": "colour",
        "color": "colour",
        "weight": "weight_g",
        "weight_g": "weight_g",
    })

    # Pris
    if "price_yuan" in df.columns:
        df["price_yuan"] = (
            df["price_yuan"]
            .astype(str)
            .str.replace("¥", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace("nan", "", regex=False)
        )
        df["price_yuan"] = pd.to_numeric(df["price_yuan"], errors="coerce")

    # Vikt
    if "weight_g" in df.columns:
        df["weight_g"] = (
            df["weight_g"]
            .astype(str)
            .str.replace("g", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("nan", "", regex=False)
        )
        df["weight_g"] = pd.to_numeric(df["weight_g"], errors="coerce")

    return df

df = load_data()

# Säkerställ viktiga kolumner
for col in ["status", "brand", "type", "size", "colour", "price_yuan", "weight_g", "yupoo", "qc", "pic"]:
    if col not in df.columns:
        df[col] = ""

# Sidebar
st.sidebar.header("Filter")

search = st.sidebar.text_input("Sök", "")

status_options = sorted(df["status"].dropna().astype(str).unique())
brand_options = sorted(df["brand"].dropna().astype(str).unique())
type_options = sorted(df["type"].dropna().astype(str).unique())

selected_status = st.sidebar.multiselect("Status", status_options, default=status_options)
selected_brand = st.sidebar.multiselect("Brand", brand_options, default=brand_options)
selected_type = st.sidebar.multiselect("Type", type_options, default=type_options)

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

# KPI cards
col1, col2, col3, col4 = st.columns(4)

col1.metric("Items", len(filtered))
col2.metric("Total value", f"¥{filtered['price_yuan'].sum(skipna=True):,.0f}")
col3.metric("Total weight", f"{filtered['weight_g'].sum(skipna=True) / 1000:.2f} kg")
col4.metric("Brands", filtered["brand"].nunique())

st.divider()

# Tabell
st.subheader("Alla plagg")

show_cols = [
    "status",
    "brand",
    "type",
    "size",
    "colour",
    "price_yuan",
    "weight_g",
    "yupoo",
    "qc"
]

st.dataframe(
    filtered[show_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "yupoo": st.column_config.LinkColumn("Yupoo"),
        "qc": st.column_config.LinkColumn("QC"),
        "price_yuan": st.column_config.NumberColumn("Price ¥", format="¥%.0f"),
        "weight_g": st.column_config.NumberColumn("Weight g", format="%.0f g"),
    }
)

st.divider()

# Charts
left, right = st.columns(2)

with left:
    st.subheader("Plagg per märke")
    brand_count = filtered["brand"].value_counts().reset_index()
    brand_count.columns = ["brand", "count"]

    if not brand_count.empty:
        fig = px.bar(brand_count, x="brand", y="count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen data att visa.")

with right:
    st.subheader("Status")
    status_count = filtered["status"].value_counts().reset_index()
    status_count.columns = ["status", "count"]

    if not status_count.empty:
        fig = px.pie(status_count, names="status", values="count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen data att visa.")

st.divider()

# Detaljvy
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
        st.write(f"**Price:** ¥{item['price_yuan'] if pd.notna(item['price_yuan']) else '-'}")
        st.write(f"**Weight:** {item['weight_g'] if pd.notna(item['weight_g']) else '-'} g")

        if str(item.get("yupoo", "")).startswith("http"):
            st.link_button("Öppna Yupoo", item["yupoo"])

        if str(item.get("qc", "")).startswith("http"):
            st.link_button("Öppna QC", item["qc"])
