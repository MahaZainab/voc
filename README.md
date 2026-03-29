# 🛒 VoxCart – AI Voice Shopping Assistant

A conversational AI shopping assistant that helps you build a cart through voice/text, 
then redirects you to the actual retailer website to complete payment.

## ✨ Features

- 🎤 **Voice Input** — Record your order via microphone (Groq Whisper transcription)
- 🔊 **Text-to-Speech** — The AI avatar speaks back to you (gTTS)
- 🤖 **Animated AI Avatar** — Visual states: idle, listening, thinking, speaking
- 🏪 **Multi-Store Support** — Walmart, Chick-fil-A, Target, Publix, Amazon
- 🛒 **Smart Cart** — AI auto-detects items to add/remove from conversation
- 💳 **Secure Checkout** — Cart builds locally; payment is handled on the real retailer site

## 🚀 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a Groq API Key
- Sign up free at https://console.groq.com
- Create an API key

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Enter your Groq API key in the sidebar and start shopping!

## 🎙️ How to Use

1. **Select a store** from the welcome screen or sidebar
2. **Type or speak** what you want to order
3. The AI will **confirm items** and add them to your cart
4. When ready, click **"Checkout at [Store]"** to pay on the retailer's website

## 📁 File Structure

```
voice_shopping_assistant/
├── app.py           # Main Streamlit application
├── style.css        # Dark theme UI styles
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## 🔧 Models Used

| Task | Model |
|------|-------|
| Chat | `llama-3.3-70b-versatile` (via Groq) |
| Voice → Text | `whisper-large-v3` (via Groq) |
| Text → Voice | gTTS (Google Text-to-Speech, free) |

## 💡 Example Conversations

**At Chick-fil-A:**
> You: "I want a spicy deluxe combo with lemonade and waffle fries"
> VoxCart: "Got it! Adding a Spicy Deluxe Combo with lemonade and waffle fries. Anything else?"

**At Walmart:**
> You: "Add 2 gallons of milk and some eggs"
> VoxCart: "Added 2 gallons of milk and a dozen eggs to your cart. Want anything else?"

## ⚠️ Notes

- Payment is **always handled on the retailer's official website** — VoxCart never handles financial data
- The checkout button links directly to the retailer's search/cart page
- Voice recording requires `audiorecorder` package and microphone permissions
