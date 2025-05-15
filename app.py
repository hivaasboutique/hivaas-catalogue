import streamlit as st
import pandas as pd
from PIL import Image
import urllib.parse
import json

# Load product data from Excel
df = pd.read_excel("products.xlsx")
df["sizes"] = df["sizes"].apply(json.loads)
df["images"] = df.apply(lambda row: [f"images/{row[col]}" for col in ["image1", "image2", "image3"] if pd.notna(row[col])], axis=1)

# Session state initialization
if "wishlist" not in st.session_state or not isinstance(st.session_state["wishlist"], dict):
    st.session_state["wishlist"] = {}
if "messages" not in st.session_state:
    st.session_state["messages"] = {}

# Sidebar styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #f2e6ff;
    }
    a.whatsapp-button > button {
        background-color: #25D366;
        color: white;
        border: none;
        padding: 8px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    }
    a.whatsapp-button > button:hover {
        background-color: #1DA851;
    }
    </style>
""", unsafe_allow_html=True)

# Banner
st.image("images/banner.png", use_container_width=True)

# Sidebar filters
st.sidebar.title("Filters")
price_sort = st.sidebar.radio("Sort by Price", ["None", "Low to High", "High to Low"])
selected_sizes = st.sidebar.multiselect("Select Sizes", ["XS", "S", "M", "L", "XL", "XXL", "XXXL"])
selected_types = st.sidebar.multiselect("Select Product Type", df["type"].unique().tolist())
search_query = st.sidebar.text_input("🔍 Search product by keyword or code", "")

# Size guide
with st.expander("📏 Size Guide"):
    st.image("images/size_guide.png", use_container_width=True)

# Filters
filtered = df.copy()
if search_query:
    mask = (
        filtered["description"].str.contains(search_query, case=False, na=False) |
        filtered["product_code"].str.contains(search_query, case=False, na=False)
    )
    filtered = filtered[mask]
if selected_sizes:
    filtered = filtered[filtered["sizes"].apply(lambda sz: any(sz.get(s, False) for s in selected_sizes))]
if selected_types:
    filtered = filtered[filtered["type"].isin(selected_types)]
if price_sort == "Low to High":
    filtered = filtered.sort_values("price")
elif price_sort == "High to Low":
    filtered = filtered.sort_values("price", ascending=False)

# Catalog Title
st.title("Hivaas Product Catalogue")

# Main Display Loop
for _, row in filtered.iterrows():
    code = row["product_code"]
    sizes = row["sizes"]
    img_key = f"{code}_img_index"

    if img_key not in st.session_state:
        st.session_state[img_key] = 0

    col1, col2 = st.columns([1, 2])
    with col1:
        if not row["in_stock"]:
            st.markdown("""
                <div style="position:relative;display:inline-block;">
                  <div style="
                    position:absolute; top:10px; left:-10px;
                    transform:rotate(-45deg);
                    background-color:#e63946; color:white;
                    padding:4px 40px; font-weight:bold; z-index:1;">
                    SOLD OUT
                  </div>
                </div>
            """, unsafe_allow_html=True)

        prev, _, next_ = st.columns([1, 6, 1])
        with prev:
            if st.button("◀", key=f"prev_{img_key}"):
                st.session_state[img_key] = (st.session_state[img_key] - 1) % len(row["images"])
        with next_:
            if st.button("▶", key=f"next_{img_key}"):
                st.session_state[img_key] = (st.session_state[img_key] + 1) % len(row["images"])

        st.image(Image.open(row["images"][st.session_state[img_key]]), width=300)

    with col2:
        st.subheader(f"Product Code: {code}")
        st.write(row["description"])
        st.write(f"**Price:** ₹{row['price']}")
        st.write(f"**Product Type:** {row['type']}")

        # Sizes
        selected = []
        if row["in_stock"]:
            st.markdown("**Select Sizes:**")
            for size, available in sizes.items():
                cb_key = f"{code}_size_{size}"
                checked = st.checkbox(label=size, key=cb_key, disabled=not available)
                if checked:
                    selected.append(size)
        else:
            st.caption("❌ This product is sold out. Sizes are not selectable.")
        st.session_state[f"{code}_selected_sizes"] = selected

        # WhatsApp Button (disabled if sold out)
        num = "918073879674"
        if st.button("📲 Send to WhatsApp", key=f"wa_btn_{code}", disabled=not row["in_stock"]):
            if selected:
                msg = f"Hi, I'm interested in Product Code: {code} - {row['description']}. Sizes: {', '.join(selected)}"
                wa_url = f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<meta http-equiv="refresh" content="0; url={wa_url}" />', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Please select the sizes in which you want this product.")

        # Wishlist Button (disabled if sold out)
        in_wishlist = code in st.session_state["wishlist"]
        btn_label = "❌ Remove from Wishlist" if in_wishlist else "❤️ Add to Wishlist"
        if st.button(btn_label, key=f"wl_{code}", disabled=not row["in_stock"]):
            if selected:
                if in_wishlist:
                    del st.session_state["wishlist"][code]
                    for size in sizes:
                        cb_key = f"{code}_size_{size}"
                        if cb_key in st.session_state:
                            del st.session_state[cb_key]
                    st.success(f"{code} removed from wishlist.")
                else:
                    st.session_state["wishlist"][code] = selected
                    st.success(f"{code} added to wishlist.")
                st.rerun()
            else:
                st.warning("⚠️ Please select the sizes in which you want this product to add to Wishlist.")

    st.markdown("---")

# Wishlist Summary
with st.sidebar:
    st.markdown("### 💖 Your Wishlist")
    if st.session_state["wishlist"]:
        lines = []
        for code, sizes in st.session_state["wishlist"].items():
            prod = df[df["product_code"] == code].iloc[0]
            st.write(f"- {code} ({', '.join(sizes)})")
            lines.append(f"{code}: {prod['description']} (₹{prod['price']}) Sizes: {', '.join(sizes)}")
        full_msg = "Hi, I'm interested in the following products:\n" + "\n".join(lines)
        wa_url = f"https://wa.me/{num}?text={urllib.parse.quote(full_msg)}"
        st.markdown(f'<a class="whatsapp-button" href="{wa_url}" target="_blank">'
                    '📲 Send Wishlist on WhatsApp</a>', unsafe_allow_html=True)
    else:
        st.markdown("💤 No items in wishlist yet.")
