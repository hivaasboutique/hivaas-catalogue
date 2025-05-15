import streamlit as st
import pandas as pd
from PIL import Image, ExifTags
import urllib.parse
import json
import requests
from io import BytesIO

@st.cache_data(show_spinner=False)
def fetch_image_from_url(url):
    response = requests.get(url)
    return response.content


# ------------------- Load and Fix Image Orientation -------------------

def load_image_corrected(path):
    img = Image.open(path)
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break
        exif = img._getexif()
        if exif is not None:
            orientation = exif.get(orientation)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img

# ------------------- Load product data -------------------

df = pd.read_excel("dummy1.xlsx")

# Handle JSON parsing safely (to avoid TypeError if NaN)
def parse_json_safe(val):
    if isinstance(val, str):
        return json.loads(val)
    return {}

df["sizes"] = df["sizes"].apply(parse_json_safe)

df["images"] = df.apply(lambda row: [row[col] for col in ["image1", "image2", "image3", "image4"] if pd.notna(row[col])], axis=1)


# ------------------- Session state initialization -------------------

if "wishlist" not in st.session_state or not isinstance(st.session_state["wishlist"], dict):
    st.session_state["wishlist"] = {}
if "messages" not in st.session_state:
    st.session_state["messages"] = {}

# ------------------- Sidebar styling -------------------

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

# ------------------- Banner -------------------

st.image("images/banner.png", use_container_width=True)

# ------------------- Sidebar Filters -------------------

st.sidebar.title("Filters")
price_sort = st.sidebar.radio("Sort by Price", ["None", "Low to High", "High to Low"])
selected_sizes = st.sidebar.multiselect("Select Sizes", ["XS", "S", "M", "L", "XL", "2XL", "3XL"])
selected_types = st.sidebar.multiselect("Select Product Type", df["type"].unique().tolist())
search_query = st.sidebar.text_input("🔍 Search product by keyword or code", "")

# ------------------- Size Guide -------------------

with st.expander("📏 Size Guide"):
    st.image("images/size_guide.png", use_container_width=True)

# ------------------- Filters -------------------

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

# ------------------- Catalog Display -------------------

st.title("Hivaas Product Catalogue")

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

        nav1, nav2 = st.columns([1, 1])
        with nav1:
            if st.button("◀", key=f"prev_{img_key}"):
                st.session_state[img_key] = (st.session_state[img_key] - 1) % len(row["images"])
        with nav2:
            if st.button("▶", key=f"next_{img_key}"):
                st.session_state[img_key] = (st.session_state[img_key] + 1) % len(row["images"])

        img_url = row["images"][st.session_state[img_key]]
        image_bytes = fetch_image_from_url(img_url)
        img = load_image_corrected(BytesIO(image_bytes))
        st.image(img, use_container_width=True)

    with col2:
        st.subheader(f"Product Code: {code}")
        st.write(row["description"])
        st.write(f"**Price:** ₹{row['price']}")
        st.write(f"**Product Type:** {row['type']}")

        st.markdown("**Select Sizes:**")
        selected = []
        for size, available in sizes.items():
            cb_key = f"{code}_size_{size}"
            checked = st.checkbox(label=size, key=cb_key, disabled=not available)
            if checked:
                selected.append(size)
        st.session_state[f"{code}_selected_sizes"] = selected

        # Disable buttons if out of stock
        disabled = not row["in_stock"]

        # WhatsApp Button
        num = "918073879674"
        if st.button("📲 Send to WhatsApp", key=f"wa_btn_{code}", disabled=disabled):
            if selected:
                msg = f"Hi, I'm interested in Product Code: {code} - {row['description']}. Sizes: {', '.join(selected)}"
                wa_url = f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<meta http-equiv="refresh" content="0; url={wa_url}" />', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Please select the sizes in which you want this product.")

        # Wishlist Button
        in_wishlist = code in st.session_state["wishlist"]
        btn_label = "❌ Remove from Wishlist" if in_wishlist else "❤️ Add to Wishlist"
        if st.button(btn_label, key=f"wl_{code}", disabled=disabled):
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

# ------------------- Wishlist Summary -------------------

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
