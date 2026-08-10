import asyncio
import logging
import os
import sys
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import Config

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure system encodings are set to prevent errors on Windows console outputs if logged
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

# Import handlers and globals from the root bot.py
from bot import (
    start_command, help_command, status_command, revenue_command,
    check_command, subscribe_command, unsubscribe_command, machines_command,
    teststart_command, testend_command, reply_text_button_handler,
    run_monitoring_check, send_revenue_report_card, post_init,
    tracker
)

# Initialize Flask application
app = Flask(__name__)

# Initialize Telegram Application
bot_app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

# Configure Handlers (same as in bot.py)
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(CommandHandler("status", status_command))
bot_app.add_handler(CommandHandler("revenue", revenue_command))
bot_app.add_handler(CommandHandler("check", check_command))
bot_app.add_handler(CommandHandler("subscribe", subscribe_command))
bot_app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
bot_app.add_handler(CommandHandler("machines", machines_command))
bot_app.add_handler(CommandHandler("teststart", teststart_command))
bot_app.add_handler(CommandHandler("testend", testend_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_text_button_handler))

# Helper to run async code synchronously in Flask handler threads
def run_async(coro):
    return asyncio.run(coro)

# Global flag to track initialization status
initialized = False

async def init_bot_app():
    global initialized
    if not initialized:
        # Run standard python-telegram-bot application lifecycle initialization
        await bot_app.initialize()
        await bot_app.start()
        # Initialize menu commands if defined
        try:
            await post_init(bot_app)
        except Exception as e:
            logger.error(f"Error executing post_init configuration: {e}")
        initialized = True

@app.route("/", methods=["GET"])
def home():
    return "Clean24 Speed Queen Telegram Bot is active and running on Vercel Serverless!"

@app.route("/api/webhook", methods=["POST"])
def webhook():
    """
    Inbound Webhook endpoint for Telegram updates.
    """
    try:
        run_async(init_bot_app())
        update_json = request.get_json(force=True)
        update = Update.de_json(update_json, bot_app.bot)
        run_async(bot_app.process_update(update))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cron/check", methods=["GET", "POST"])
def cron_check():
    """
    Cron endpoint called every 60 seconds (by external pinger) to check machine state transitions.
    """
    try:
        run_async(init_bot_app())
        logger.info("Triggering periodic status check via cron...")
        run_async(run_monitoring_check(bot_app))
        return jsonify({"status": "monitoring check completed"}), 200
    except Exception as e:
        logger.error(f"Error executing periodic status check cron: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cron/revenue", methods=["GET", "POST"])
def cron_revenue():
    """
    Cron endpoint called daily (at 10:40 PM Phnom Penh time / 3:40 PM UTC) to send the revenue card.
    """
    try:
        run_async(init_bot_app())
        logger.info("Triggering daily scheduled revenue card broadcast...")
        run_async(send_revenue_report_card(bot_app, tracker.subscribed_chats))
        return jsonify({"status": "daily revenue report broadcast completed"}), 200
    except Exception as e:
        logger.error(f"Error executing daily scheduled revenue card cron: {e}")
        return jsonify({"error": str(e)}), 500
