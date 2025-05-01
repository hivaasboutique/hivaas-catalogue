import streamlit as st
import pandas as pd
from PIL import Image
import urllib.parse

# Sample product data
products = [
    {
        "images": ["images/111.jpg", "images/222.jpg", "images/333.jpg"],
        "product_code": "HK001",
        "description": "Elegant cotton kurthi top with floral prints.",
        "price": 799,
        "sizes": {"S": True, "M": False, "L": True},
        "type": "kurthi tops",
        "in_stock": True
    },
    {
        "images": ["images/222.jpg", "images/333.jpg"],
        "product_code": "HSK002",
        "description": "Trendy short kurti with mirror work.",
        "price": 599,
        "sizes": {"XS": False, "S": True, "M": False},
        "type": "short kurtis",
        "in_stock": False
    },
    {
        "images": ["images/333.jpg", "images/111.jpg"],
        "product_code": "HCS003",
        "description": "Traditional chudidhar set with dupatta.",
        "price": 1299,
        "sizes": {"M": True, "L": True, "XL": True, "XXL": True},
        "type": "chudidhar sets",
        "in_stock": True
    },
]

df = pd.DataFrame(products)

# Session state for wishlist
if "wishlist" not in st.session_state:
    st.session_state["wishlist"] = []

# Sidebar styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #f2e6ff;
    }
    </style>
""", unsafe_allow_html=True)

# Banner
st.image("images/banner.png", use_container_width=True)

# Sidebar Filters
st.sidebar.title("Filters")
price_sort     = st.sidebar.radio("Sort by Price", ["None", "Low to High", "High to Low"])
selected_sizes = st.sidebar.multiselect("Select Sizes", ["XS", "S", "M", "L", "XL", "XXL", "XXXL"])
selected_types = st.sidebar.multiselect("Select Product Type", ["kurthi tops", "short kurtis", "chudidhar sets"])
search_query   = st.sidebar.text_input("🔍 Search product by keyword or code", "")

# Size Guide
with st.expander("📏 Size Guide"):
    st.image("images/size_guide.png", use_container_width=True)

# Filtering
filtered = df.copy()
if search_query:
    filtered = filtered[
        filtered["description"].str.contains(search_query, case=False) |
        filtered["product_code"].str.contains(search_query, case=False)
    ]
if selected_sizes:
    filtered = filtered[filtered["sizes"].apply(lambda L: any(s in L for s in selected_sizes))]
if selected_types:
    filtered = filtered[filtered["type"].isin(selected_types)]
if price_sort == "Low to High":
    filtered = filtered.sort_values("price")
elif price_sort == "High to Low":
    filtered = filtered.sort_values("price", ascending=False)

st.title("Hivaas Product Catalogue")

# Product Display
for _, row in filtered.iterrows():
    img_key = f"{row['product_code']}_img_index"
    if img_key not in st.session_state:
        st.session_state[img_key] = 0

    col1, col2 = st.columns([1, 2])
    with col1:
        # SOLD OUT Ribbon
        if not row["in_stock"]:
            st.markdown("""
                <div style="position: relative; display: inline-block;">
                    <div style="position: absolute; top: 10px; left: -10px; transform: rotate(-45deg);
                                background-color: #e63946; color: white; padding: 4px 40px;
                                font-weight: bold; z-index: 1;">
                        SOLD OUT
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Image Navigation
        prev, _, next_ = st.columns([1, 6, 1])
        with prev:
            if st.button("◀", key=f"prev_{img_key}"):
                st.session_state[img_key] = (st.session_state[img_key] - 1) % len(row["images"])
        with next_:
            if st.button("▶", key=f"next_{img_key}"):
                st.session_state[img_key] = (st.session_state[img_key] + 1) % len(row["images"])

        current_img = row["images"][st.session_state[img_key]]
        st.image(Image.open(current_img), width=300)

    with col2:
        st.subheader(f"Product Code: {row['product_code']}")
        st.write(row["description"])
        st.write(f"**Price:** ₹{row['price']}")
        size_display = []
        for size, available in row["sizes"].items():
            if available:
                size_display.append(f"🟢 {size}")
            else:
                size_display.append(f"⚪️ ~~{size}~~")
        st.write("**Sizes:** " + " | ".join(size_display))

        st.write(f"**Product Type:** {row['type']}")

        # WhatsApp link
        num = "918073879674"
        msg = f"Hi, I'm interested in Product Code: {row['product_code']} - {row['description']}."
        wa_url = f"https://wa.me/{num}?text={msg.replace(' ', '%20')}"
        st.markdown(f"[Click here to send this product to us on WhatsApp](<{wa_url}>)", unsafe_allow_html=True)

        # Wishlist checkbox toggle
        code = row["product_code"]
        cb_key = f"cb_{code}"
        checked = st.checkbox("❤️ In Wishlist", key=cb_key)

        # Handle add/remove after checkbox renders
        if checked and code not in st.session_state["wishlist"]:
            st.session_state["wishlist"].append(code)
        elif not checked and code in st.session_state["wishlist"]:
            st.session_state["wishlist"].remove(code)


    st.markdown("---")

# Wishlist Summary in Sidebar
if st.session_state["wishlist"]:
    with st.sidebar:
        st.markdown("### 💖 Your Wishlist")
        for code in st.session_state["wishlist"]:
            st.write(f"- {code}")

        # WhatsApp Wishlist
        wishlist_products = df[df["product_code"].isin(st.session_state["wishlist"])]
        lines = [f"{prod['product_code']}: {prod['description']} (₹{prod['price']})"
                 for _, prod in wishlist_products.iterrows()]
        message = "Hi, I'm interested in the following products:\n" + "\n".join(lines)
        encoded = urllib.parse.quote(message)
        url = f"https://wa.me/{num}?text={encoded}"
        st.sidebar.markdown(f"[📲 Send Wishlist on WhatsApp]({url})", unsafe_allow_html=True)
else:
    st.sidebar.markdown("💤 No items in wishlist yet.")
