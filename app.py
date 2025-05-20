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

# ------------------- Styling -------------------

st.markdown("""
    <style>
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

# ------------------- Top Filters -------------------

st.header("🛍️ Hivaas Product Catalogue")

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1:
    price_sort = st.radio("Sort by Price", ["None", "Low to High", "High to Low"], horizontal=True)
with col2:
    selected_sizes = st.multiselect("Select Sizes", ["XS", "S", "M", "L", "XL", "2XL", "3XL"])
with col3:
    selected_types = st.multiselect("Select Product Type", df["type"].unique().tolist())
with col4:
    search_query = st.text_input("🔍 Search by keyword or code")

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

# ------------------- Wishlist Summary -------------------

with st.expander("💖 Your Wishlist"):
    if st.session_state["wishlist"]:
        lines = []
        for code, sizes in st.session_state["wishlist"].items():
            prod = df[df["product_code"] == code].iloc[0]
            st.write(f"- {code} ({', '.join(sizes)})")
            lines.append(f"{code}: {prod['description']} (₹{prod['price']}) Sizes: {', '.join(sizes)}")
        full_msg = "Hi, I'm interested in the following products:\n" + "\n".join(lines)
        wa_url = f"https://wa.me/918073879674?text={urllib.parse.quote(full_msg)}"
        st.markdown(f'<a class="whatsapp-button" href="{wa_url}" target="_blank">'
                    '📲 Send Wishlist on WhatsApp</a>', unsafe_allow_html=True)
    else:
        st.markdown("💤 No items in wishlist yet.")

# ------------------- Pagination -------------------

products_per_page = 10
total_products = len(filtered)
if total_products == 0:
    st.markdown("""
        <div style="background-color:#fff3cd;padding:20px;border-radius:10px;border:1px solid #ffeeba;margin-top:20px;">
            <h4 style="color:#856404;">😔 Sorry, we don't have anything matching your search right now.</h4>
            <p style="color:#856404;">Try changing your filters or search term.</p>
        </div>
    """, unsafe_allow_html=True)

    # Clear Filters button
    #if st.button("🔄 Clear Filters & Search"):
        #st.session_state["pagination_input"] = 1
        #st.experimental_rerun()

    # ---------------- Show similar products suggestion ----------------
    st.markdown("### 🧡 You might like these instead")

    # Optionally base suggestions on selected type, else show general fallback
    suggestion_base = df.copy()
    if selected_types:
        suggestion_base = suggestion_base[suggestion_base["type"].isin(selected_types)]
    if selected_sizes:
        suggestion_base = suggestion_base[suggestion_base["sizes"].apply(lambda sz: any(sz.get(s, False) for s in selected_sizes))]

    suggestion_base = suggestion_base.head(5)

    if suggestion_base.empty:
        suggestion_base = df.sample(min(5, len(df)))  # Show random fallback if nothing fits

    for _, row in suggestion_base.iterrows():
        st.markdown(f"**{row['product_code']}** — ₹{row['price']} — {row['description']}")
        img_url = row["images"][0] if row["images"] else None
        if img_url:
            image_bytes = fetch_image_from_url(img_url)
            img = load_image_corrected(BytesIO(image_bytes))
            st.image(img, width=200)
        st.markdown("---")
else:
    total_pages = (total_products - 1) // products_per_page + 1
    page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, key="pagination_input")
    start_idx = (page_number - 1) * products_per_page
    end_idx = start_idx + products_per_page
    paginated_df = filtered.iloc[start_idx:end_idx]

# ------------------- Product Display -------------------

    for _, row in paginated_df.iterrows():
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

            prev, _, next_ = st.columns([1, 3, 1])
            with prev:
                if st.button("◀", key=f"prev_{img_key}"):
                    st.session_state[img_key] = (st.session_state[img_key] - 1) % len(row["images"])
            with next_:
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

            disabled = not row["in_stock"]

            # WhatsApp Button
            num = "918073879674"
            msg = f"Hi, I'm interested in Product Code: {code} - {row['description']}. Sizes: {', '.join(selected)}"
            wa_url = f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"

            if selected and not disabled:
                st.markdown(
                    f'<a href="{wa_url}" target="_blank" style="text-decoration:none;">'
                    f'<button style="background-color:#25D366;color:white;padding:8px 12px;border:none;border-radius:4px;cursor:pointer;">📲 Send to WhatsApp</button></a>',
                    unsafe_allow_html=True
                )
            elif disabled:
                st.button("📲 Send to WhatsApp", disabled=True)
            else:
                st.warning("⚠️ Please select the sizes in which you want this product before sending it to us on Whatsapp.")
                st.button("📲 Send to WhatsApp", disabled=True)

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