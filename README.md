# 🧺 Clean24 Machine VS - Speed Queen Insights Telegram Bot 🇰🇭

Real-time Telegram Bot integration for **Clean24 Veng Sreng** (Speed Queen Room ID `23546` / SID `1517969`).

---

## 🌟 Key Features

1. **📊 Real-Time Machine Status (W1 - D10)**:
   - Full Khmer UI monitoring 10 machines (Washer Extractor 9kg/14kg/18kg & Tumbler Dryers 14kg Stack).
   - Groups machines by status: 🟢 **Available**, 🔵 **Running**, 🔴 **Out of Service**.

2. **💰 Live Speed Queen Daily Revenue API Integration**:
   - Queries Speed Queen Insights financial report API (`LOCATION_AND_REVENUE`) in real-time.
   - Automatically calculates daily total revenue (៛122,000 / $30.50 USD) and total cycle turns.

3. **⏰ Scheduled Daily Revenue Card (10:40 PM)**:
   - Automated cron job broadcasts the exact daily financial report card to Telegram every night at **10:40 PM** (Phnom Penh local time).

4. **🚀 Strict START & END Machine Cycle Alerts**:
   - Sends instant Telegram alerts when a machine **STARTS** a cycle or **FINISHES/ENDS** a cycle.

5. **🔘 Persistent Reply Keyboard & Menu Buttons**:
   - Interactive bottom-bar buttons (`📊 ស្ថានភាពម៉ាស៊ីន`, `💰 របាយការណ៍ចំណូល`, `🔄 ពិនិត្យភ្លាមៗ`, `🧺 បញ្ជីម៉ាស៊ីន W1-D10`) and Telegram `Menu` integration.

---

## 🚀 Quick Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/PPCUPDATE/Clean24Machine_VS.git
cd Clean24Machine_VS
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 4. Run the Bot
```bash
python bot.py
```

---

## 📋 Bot Commands

- `/start` - Start bot and activate persistent keyboard buttons
- `/status` - Check current real-time machine status (W1 - D10)
- `/revenue` - Fetch live daily revenue report
- `/check` - Trigger manual status refresh check
- `/machines` - View full list of 10 machines and capacities
- `/help` - View usage guide
