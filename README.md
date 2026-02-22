# Mercadona Grocery Health Analyzer Bot

A Telegram bot that analyzes Mercadona supermarket receipts, translates items from Catalan/Spanish to English, scores your grocery basket from A to E, and provides personalized diet recommendations.

## Features

- **Receipt scanning** — Send a photo of your Mercadona receipt and get instant analysis
- **ABCDE scoring** — Every item scored on nutritional quality, with an overall basket grade
- **Visual score card** — Beautiful chart showing your grade, category breakdown, and spending
- **Smart recommendations** — AI-powered diet tips specific to Mercadona products
- **Trend tracking** — See how your shopping habits improve over time
- **Weekly reports** — Automatic Sunday summary of your shopping health
- **Streak tracking** — Keep your healthy shopping streak alive

## Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd eatright
pip install -r requirements.txt
```

### 2. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 3. Get a Google Gemini API key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create an API key

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./groceries.db
```

### 5. Run the bot

```bash
python main.py
```

## Bot Commands

| Command    | Description                              |
|------------|------------------------------------------|
| `/start`   | Welcome message and usage instructions   |
| `/history` | View your last 5 receipt scores          |
| `/stats`   | See your score trend chart over time     |
| `/tips`    | Get personalized diet recommendations    |
| `/streak`  | Check your healthy shopping streak       |
| `/compare` | Compare your last two receipts           |
| `/help`    | Show help message                        |

## How It Works

1. **Send a receipt photo** — The bot uses Gemini's vision API to read every item
2. **Items are translated** — Catalan/Spanish product names become English
3. **Each item is scored** — Based on nutritional quality (A=Excellent to E=Bad)
4. **Basket grade calculated** — Weighted by spend (more expensive items count more)
5. **Recommendations generated** — AI suggests specific Mercadona product swaps
6. **History tracked** — Your scores are stored for trend analysis

## Scoring System

| Grade | Meaning   | Examples                                         |
|-------|-----------|--------------------------------------------------|
| **A** | Excellent | Fresh produce, legumes, whole grains, water       |
| **B** | Good      | Low-fat dairy, lean meats, fish                   |
| **C** | Average   | Bread, pasta, rice, eggs                          |
| **D** | Poor      | High sugar, high sodium, ultra-processed          |
| **E** | Bad       | Soft drinks, sweets, chips, alcohol               |

## Project Structure

```
├── main.py                     # Entry point
├── bot/
│   ├── handlers.py             # Telegram command & message handlers
│   ├── keyboards.py            # Inline keyboard builders
│   └── messages.py             # Message templates
├── core/
│   ├── receipt_parser.py       # Gemini vision receipt extraction
│   ├── nutritional_scorer.py   # ABCDE scoring logic
│   ├── diet_advisor.py         # AI recommendation engine
│   └── predictive_engine.py    # Trend tracking & predictions
├── database/
│   ├── models.py               # SQLAlchemy models
│   └── repository.py           # Database operations
├── charts/
│   └── visualizer.py           # Score card & trend chart generation
└── tests/
    ├── test_receipt_parser.py
    └── test_scorer.py
```

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Tech Stack

- **Python 3.11+**
- **python-telegram-bot** v21 (async)
- **Google Gemini 2.5 Flash** (vision + text)
- **SQLite** + SQLAlchemy
- **Matplotlib** + Pillow (charts)
- **APScheduler** (weekly reports)
