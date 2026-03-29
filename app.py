import streamlit as st
import json
import re
from groq import Groq
from gtts import gTTS
import base64
import io


# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VoxCart – Voice Shopping Assistant",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load CSS ────────────────────────────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Session State Init ──────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "cart" not in st.session_state:
    st.session_state.cart = []
if "selected_store" not in st.session_state:
    st.session_state.selected_store = None
if "avatar_state" not in st.session_state:
    st.session_state.avatar_state = "idle"  # idle | listening | thinking | speaking
if "groq_client" not in st.session_state:
    # Auto-load from Streamlit secrets (for cloud deployment)
    api_key = st.secrets.get("GROQ_API_KEY", "")
    st.session_state.groq_client = Groq(api_key=api_key) if api_key else None

# ── Store Config ────────────────────────────────────────────────────────────────
STORES = {
    "Walmart": {
        "emoji": "🔵",
        "color": "#0071CE",
        "search_url": "https://www.walmart.com/search?q=",
        "cart_url": "https://www.walmart.com/cart",
        "specialty": "groceries, electronics, household items",
    },
    "Chick-fil-A": {
        "emoji": "🐔",
        "color": "#DD0031",
        "search_url": "https://www.chick-fil-a.com/menu",
        "cart_url": "https://www.chick-fil-a.com/order",
        "specialty": "chicken sandwiches, nuggets, salads, waffle fries",
    },
    "Target": {
        "emoji": "🎯",
        "color": "#CC0000",
        "search_url": "https://www.target.com/s?searchTerm=",
        "cart_url": "https://www.target.com/co-cart",
        "specialty": "clothing, home goods, electronics, groceries",
    },
    "Publix": {
        "emoji": "🟢",
        "color": "#007A33",
        "search_url": "https://www.publix.com/pd/search?query=",
        "cart_url": "https://www.publix.com/shopping/cart",
        "specialty": "fresh groceries, deli, bakery, pharmacy",
    },
    "Amazon": {
        "emoji": "📦",
        "color": "#FF9900",
        "search_url": "https://www.amazon.com/s?k=",
        "cart_url": "https://www.amazon.com/gp/cart/view.html",
        "specialty": "everything — electronics, books, household, clothing",
    },
}

# ── System Prompt ───────────────────────────────────────────────────────────────
def build_system_prompt(store: str) -> str:
    info = STORES[store]
    return f"""You are VoxCart, a friendly and efficient voice shopping assistant for {store}.
Store specialty: {info['specialty']}

Your role:
1. Help users find and add items to their cart through natural conversation
2. Suggest popular or related items when relevant
3. Keep track of what the user wants to order
4. When the user is ready to checkout, summarize their cart and direct them to complete payment on the {store} website

Rules:
- Be concise and conversational (you're a voice assistant — short replies)
- When a user says they want something, confirm it and add it to their mental cart
- Respond with JSON when the user adds/removes items or is ready to checkout
- For normal conversation, respond with plain text only

JSON format for cart updates (ONLY when adding/removing items):
{{"action": "add"|"remove"|"checkout"|"clear", "item": "item name", "quantity": 1, "store": "{store}"}}

For checkout action: {{"action": "checkout", "store": "{store}", "summary": "brief cart summary"}}

Be warm, helpful, and keep responses under 3 sentences unless listing items."""


# ── Groq Chat ───────────────────────────────────────────────────────────────────
def chat_with_groq(user_message: str, store: str) -> str:
    if not st.session_state.groq_client:
        return "⚠️ Please add your Groq API key in the sidebar to start!"

    history = [{"role": "system", "content": build_system_prompt(store)}]
    for msg in st.session_state.messages[-10:]:  # last 10 for context
        history.append({"role": msg["role"], "content": msg["content"]})
    history.append({"role": "user", "content": user_message})

    try:
        completion = st.session_state.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history,
            temperature=0.7,
            max_tokens=512,
            stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


# ── Parse AI Response ───────────────────────────────────────────────────────────
def parse_response(response: str):
    """Extract JSON action and clean text from AI response."""
    json_pattern = r'\{[^{}]*"action"[^{}]*\}'
    match = re.search(json_pattern, response, re.DOTALL)
    action_data = None
    clean_text = response

    if match:
        try:
            action_data = json.loads(match.group())
            clean_text = response.replace(match.group(), "").strip()
        except json.JSONDecodeError:
            pass

    return action_data, clean_text


# ── Cart Operations ─────────────────────────────────────────────────────────────
def update_cart(action_data: dict):
    action = action_data.get("action")
    item = action_data.get("item", "")
    qty = action_data.get("quantity", 1)

    if action == "add":
        # Check if item already in cart
        for cart_item in st.session_state.cart:
            if cart_item["item"].lower() == item.lower():
                cart_item["quantity"] += qty
                return
        st.session_state.cart.append({"item": item, "quantity": qty, "store": action_data.get("store", "")})

    elif action == "remove":
        st.session_state.cart = [
            c for c in st.session_state.cart
            if c["item"].lower() != item.lower()
        ]
    elif action == "clear":
        st.session_state.cart = []


# ── Text-to-Speech ──────────────────────────────────────────────────────────────
def text_to_speech(text: str) -> str | None:
    """Convert text to base64 audio using gTTS."""
    try:
        clean = re.sub(r'[{}\[\]"\':]', '', text)[:300]
        tts = gTTS(text=clean, lang='en', slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception:
        return None


def autoplay_audio(b64_audio: str):
    audio_html = f"""
    <audio autoplay style="display:none">
        <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
    </audio>"""
    st.markdown(audio_html, unsafe_allow_html=True)


# ── Build Checkout URL ──────────────────────────────────────────────────────────
def build_checkout_url(store: str) -> str:
    if not st.session_state.cart:
        return STORES[store]["cart_url"]

    first_item = st.session_state.cart[0]["item"].replace(" ", "+")
    base = STORES[store]["search_url"]

    if store == "Chick-fil-A":
        return STORES[store]["cart_url"]
    return f"{base}{first_item}"


# ══════════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

# ── Sidebar: API Key + Store Select ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-header">⚙️ Settings</div>', unsafe_allow_html=True)

    # Show connected if loaded from secrets, else allow manual entry
    if st.session_state.groq_client:
        st.success("✅ Connected via Secrets")
    else:
        manual_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
        if manual_key:
            st.session_state.groq_client = Groq(api_key=manual_key)
            st.success("✅ Connected")
            st.rerun()

    st.markdown("---")
    st.markdown("**🏪 Select Store**")
    for store_name, info in STORES.items():
        if st.button(
            f"{info['emoji']} {store_name}",
            key=f"store_{store_name}",
            use_container_width=True,
        ):
            st.session_state.selected_store = store_name
            st.session_state.messages = []
            st.session_state.cart = []
            st.rerun()

    if st.session_state.selected_store:
        st.markdown(f"**Active:** {STORES[st.session_state.selected_store]['emoji']} {st.session_state.selected_store}")

    st.markdown("---")
    st.markdown("**🛒 Cart**")
    if st.session_state.cart:
        for item in st.session_state.cart:
            st.markdown(f"• {item['quantity']}x {item['item']}")
        st.markdown("---")
        if st.button("🗑️ Clear Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
    else:
        st.markdown("*Cart is empty*")


# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="logo-text">🛒 VoxCart</div>
    <div class="tagline">Your AI Voice Shopping Assistant</div>
</div>
""", unsafe_allow_html=True)

# ── Store Selection (main area if none selected) ────────────────────────────────
if not st.session_state.selected_store:
    st.markdown('<div class="store-select-prompt">Choose a store to begin shopping</div>', unsafe_allow_html=True)

    cols = st.columns(len(STORES))
    for i, (store_name, info) in enumerate(STORES.items()):
        with cols[i]:
            if st.button(
                f"{info['emoji']}\n\n**{store_name}**",
                key=f"main_store_{store_name}",
                use_container_width=True,
                help=info["specialty"],
            ):
                st.session_state.selected_store = store_name
                welcome = f"Hey there! I'm VoxCart, your {store_name} assistant. What would you like to order today? We've got great {info['specialty']}!"
                st.session_state.messages.append({"role": "assistant", "content": welcome})
                st.rerun()

    st.stop()

# ── Main Layout: Avatar + Chat ──────────────────────────────────────────────────
store = st.session_state.selected_store
store_info = STORES[store]

left_col, right_col = st.columns([1, 2], gap="large")

# ── LEFT: Avatar Panel ──────────────────────────────────────────────────────────
with left_col:
    avatar_state = st.session_state.avatar_state
    anim_class = f"avatar-{avatar_state}"

    st.markdown(f"""
    <div class="avatar-panel">
        <div class="store-badge" style="background:{store_info['color']}20; border-color:{store_info['color']}40">
            {store_info['emoji']} {store}
        </div>
        <div class="avatar-wrapper {anim_class}">
            <div class="avatar-face">
                <div class="avatar-eyes">
                    <div class="eye left-eye"><div class="pupil"></div></div>
                    <div class="eye right-eye"><div class="pupil"></div></div>
                </div>
                <div class="avatar-mouth {'talking' if avatar_state == 'speaking' else ''}"></div>
            </div>
            <div class="avatar-body"></div>
            <div class="avatar-rings">
                <div class="ring r1"></div>
                <div class="ring r2"></div>
                <div class="ring r3"></div>
            </div>
        </div>
        <div class="avatar-status">{
            '💤 Ready' if avatar_state == 'idle'
            else '🎤 Listening...' if avatar_state == 'listening'
            else '🤔 Thinking...' if avatar_state == 'thinking'
            else '🔊 Speaking...'
        }</div>
        <div class="cart-count-badge">
            🛒 {sum(i['quantity'] for i in st.session_state.cart)} item{'s' if sum(i['quantity'] for i in st.session_state.cart) != 1 else ''} in cart
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Cart preview
    if st.session_state.cart:
        st.markdown('<div class="cart-preview-title">🛒 Your Cart</div>', unsafe_allow_html=True)
        for item in st.session_state.cart:
            st.markdown(f"""
            <div class="cart-item-row">
                <span class="cart-qty">{item['quantity']}×</span>
                <span class="cart-name">{item['item']}</span>
            </div>""", unsafe_allow_html=True)

        checkout_url = build_checkout_url(store)
        st.markdown(f"""
        <a href="{checkout_url}" target="_blank" class="checkout-btn" 
           style="background:{store_info['color']}">
            💳 Checkout at {store} →
        </a>""", unsafe_allow_html=True)


# ── RIGHT: Chat Panel ────────────────────────────────────────────────────────────
with right_col:
    st.markdown('<div class="chat-panel">', unsafe_allow_html=True)

    # Chat history
    chat_container = st.container(height=420)
    with chat_container:
        if not st.session_state.messages:
            st.markdown(f"""
            <div class="welcome-bubble">
                👋 Hey! I'm your <strong>{store}</strong> assistant.<br>
                Tell me what you'd like to order — I'll help build your cart!
            </div>""", unsafe_allow_html=True)
        else:
            for msg in st.session_state.messages:
                role_class = "user-bubble" if msg["role"] == "user" else "ai-bubble"
                prefix = "🧑 You" if msg["role"] == "user" else f"{store_info['emoji']} VoxCart"
                st.markdown(f"""
                <div class="chat-bubble {role_class}">
                    <div class="bubble-sender">{prefix}</div>
                    <div class="bubble-text">{msg['content']}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Input Row ────────────────────────────────────────────────────────────────
    st.markdown('<div class="input-row">', unsafe_allow_html=True)

    input_col, btn_col = st.columns([5, 1])
    with input_col:
        user_input = st.text_input(
            "Message",
            placeholder=f"e.g. 'I'd like a spicy chicken sandwich and large fries'",
            label_visibility="collapsed",
            key="chat_input",
        )
    with btn_col:
        send_clicked = st.button("Send ➤", use_container_width=True, type="primary")

    # ── Voice Input via Browser Web Speech API ─────────────────────────────────
    # Uses the browser's built-in speech recognition — no extra packages needed.
    # Works on Streamlit Cloud (Chrome/Edge).
    st.components.v1.html("""
    <style>
      #mic-btn {
        background: linear-gradient(135deg, #6c63ff, #00d4aa);
        border: none; border-radius: 50px; color: white; cursor: pointer;
        font-size: 15px; font-weight: 600; padding: 10px 28px; margin: 6px 0;
        transition: all 0.2s; width: 100%; letter-spacing: 0.03em;
      }
      #mic-btn:hover { opacity: 0.88; transform: translateY(-1px); }
      #mic-btn.recording { background: linear-gradient(135deg, #ff4757, #ff6b81); animation: pulse-rec 1s infinite; }
      #status { font-size: 12px; color: #7c84a8; margin-top: 4px; min-height: 18px; text-align: center; }
      @keyframes pulse-rec {
        0%,100% { box-shadow: 0 0 0 0 rgba(255,71,87,0.4); }
        50% { box-shadow: 0 0 0 8px rgba(255,71,87,0); }
      }
    </style>
    <button id="mic-btn" onclick="toggleMic()">🎤 Click to Speak</button>
    <div id="status">Click button, speak your order, it will auto-fill above</div>
    <script>
    let recognition = null;
    let isRecording = false;
    function toggleMic() {
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        document.getElementById('status').innerText = 'Use Chrome or Edge for voice input';
        return;
      }
      if (isRecording) { recognition.stop(); return; }
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SR();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => {
        isRecording = true;
        document.getElementById('mic-btn').classList.add('recording');
        document.getElementById('mic-btn').innerText = '⏹ Stop';
        document.getElementById('status').innerText = '🔴 Listening — speak now...';
      };
      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        document.getElementById('status').innerText = '✅ Heard: "' + transcript + '" — now click Send ➤';
        // Inject transcript into the Streamlit text input
        try {
          const inputs = window.parent.document.querySelectorAll('input[type=text]');
          for (const inp of inputs) {
            if (inp.offsetParent !== null) {
              const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
              nativeInputValueSetter.call(inp, transcript);
              inp.dispatchEvent(new Event('input', {bubbles: true}));
              break;
            }
          }
        } catch(err) { document.getElementById('status').innerText += ' (copy text manually if needed)'; }
      };
      recognition.onerror = (e) => {
        document.getElementById('status').innerText = 'Error: ' + e.error + ' — try again';
        isRecording = false;
        document.getElementById('mic-btn').classList.remove('recording');
        document.getElementById('mic-btn').innerText = '🎤 Click to Speak';
      };
      recognition.onend = () => {
        isRecording = false;
        document.getElementById('mic-btn').classList.remove('recording');
        document.getElementById('mic-btn').innerText = '🎤 Click to Speak';
      };
      recognition.start();
    }
    </script>
    """, height=95)

    # Use voice text if captured
    if "voice_text" in st.session_state and st.session_state.voice_text:
        user_input = st.session_state.voice_text
        st.session_state.voice_text = ""
        send_clicked = True

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Quick Suggestions ────────────────────────────────────────────────────────
    st.markdown('<div class="suggestions-row">', unsafe_allow_html=True)
    suggestions = {
        "Walmart": ["🛒 Weekly groceries", "📺 Electronics deals", "🧴 Household supplies"],
        "Chick-fil-A": ["🐔 Spicy deluxe combo", "🍟 12pc nuggets", "🥗 Market salad"],
        "Target": ["👕 Clothing", "🏠 Home decor", "🧴 Beauty products"],
        "Publix": ["🥖 Fresh bakery", "🥩 Deli order", "🍎 Fresh produce"],
        "Amazon": ["📦 Prime deals", "📚 Books", "🔌 Electronics"],
    }
    for s in suggestions.get(store, []):
        if st.button(s, key=f"sug_{s}"):
            user_input = s
            send_clicked = True

    st.markdown("</div>", unsafe_allow_html=True)


# ── Process Send ────────────────────────────────────────────────────────────────
if send_clicked and user_input.strip():
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.avatar_state = "thinking"

    # Get AI response
    raw_response = chat_with_groq(user_input, store)
    action_data, clean_text = parse_response(raw_response)

    # Handle cart action
    if action_data:
        update_cart(action_data)
        if action_data.get("action") == "checkout":
            checkout_url = build_checkout_url(store)
            clean_text += f"\n\n[🛒 Click here to complete your order at {store}]({checkout_url})"

    # Add AI message
    st.session_state.messages.append({"role": "assistant", "content": clean_text})
    st.session_state.avatar_state = "speaking"

    # TTS
    b64 = text_to_speech(clean_text)
    if b64:
        autoplay_audio(b64)

    st.rerun()

# Reset avatar to idle after speaking
if st.session_state.avatar_state == "speaking":
    import time
    time.sleep(0.1)
    st.session_state.avatar_state = "idle"
