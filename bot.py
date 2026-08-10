import asyncio
import logging
import os
import sys
# Set console encoding to UTF-8 to prevent UnicodeEncodeError on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
from datetime import datetime, time
import pytz
from typing import List, Set
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
    filters
)

from config import Config
from sq_client import SpeedQueenClient, MACHINE_METADATA
from tracker import StateTracker

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Global instances
sq_client = SpeedQueenClient(email=Config.SQ_EMAIL, password=Config.SQ_PASSWORD)
tracker = StateTracker()



KHMER_MONTHS = {
    1: "មករា", 2: "កុម្ភៈ", 3: "មីនា", 4: "មេសា",
    5: "ឧសភា", 6: "មិថុនា", 7: "កក្កដា", 8: "សីហា",
    9: "កញ្ញា", 10: "តុលា", 11: "វិច្ឆិកា", 12: "ធ្នូ"
}

def format_khmer_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day = f"{dt.day:02d}"
        month = KHMER_MONTHS.get(dt.month, "")
        year = dt.year
        return f"{day} {month} {year}"
    except Exception:
        return date_str


def get_persistent_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton("📊 ស្ថានភាពម៉ាស៊ីន"),
            KeyboardButton("💰 របាយការណ៍ចំណូល")
        ],
        [
            KeyboardButton("🔄 ពិនិត្យភ្លាមៗ"),
            KeyboardButton("🧺 បញ្ជីម៉ាស៊ីន W1-D10")
        ],
        [
            KeyboardButton("❓ សៀវភៅណែនាំ")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def translate_status_khmer(status: str) -> str:
    s = status.upper()
    if "AVAILABLE" in s or "IDLE" in s:
        return "ទំនេរ"
    elif "RUNNING" in s or "IN_USE" in s:
        return "កំពុងដំណើរការ"
    elif "READY" in s:
        return "ត្រៀមចាប់ផ្ដើម"
    elif "END" in s or "FINISHED" in s or "DONE" in s or "COMPLETE" in s:
        return "បោក/សម្ងួតរួចរាល់"
    elif "SERVICE" in s or "OFFLINE" in s or "ERROR" in s or "UNAVAILABLE" in s:
        return "ខូច"
    return status


def build_location_status_card(data: dict) -> str:
    if data.get("error"):
        return "⚠️ *កំហុសក្នុងការទាញយកទិន្នន័យសម្រាប់ Clean24 Veng Sreng*"

    sid = data.get("sid", "1517969")
    loc_name = data.get("location_name", "Clean24 Veng Sreng")
    counts = data.get("counts", {})

    avail_count = counts.get("AVAILABLE", 0)
    running_count = counts.get("RUNNING", 0)
    oos_count = counts.get("OUT_OF_SERVICE", 0)

    avail_lines = data.get("avail_lines", [])
    running_lines = data.get("running_lines", [])
    oos_lines = data.get("oos_lines", [])

    lines = [
        "🤖 *ការជូនដំណឹងស្វ័យប្រវត្តិ*\n",
        f"🧺 *{loc_name}*",
        f"🆔 *SID:* {sid}\n",
        "📊 *សង្ខេប*",
        f"🟢 *ទំនេរ៖* {avail_count}",
        f"🔵 *កំពុងដំណើរការ៖* {running_count}",
        f"🔴 *ខូច៖* {oos_count}\n"
    ]

    if avail_lines:
        lines.append("🟢 *ទំនេរ*")
        lines.extend(avail_lines)
        lines.append("")

    if running_lines:
        lines.append("🔵 *កំពុងដំណើរការ*")
        lines.extend(running_lines)
        lines.append("")

    if oos_lines:
        lines.append("🔴 *ខូច*")
        lines.extend(oos_lines)
        lines.append("")

    return "\n".join(lines).strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    tracker.add_subscriber(chat_id)

    sq_client.login()

    msg = (
        "🧺 *សូមស្វាគមន៍មកកាន់ Speed Queen Telegram Bot (Clean24 Veng Sreng)!*\n\n"
        "ខ្ញុំជាប្រព័ន្ធស្វ័យប្រវត្តិតាមដានស្ថានភាពម៉ាស៊ីនបោកគក់ និង របាយការណ៍ចំណូលប្រចាំថ្ងៃរបស់អ្នកក្នុងពេលជាក់ស្តែង។\n\n"
        f"📍 *លេខសំគាល់ Telegram Chat ID របស់អ្នក*: `{chat_id}` (បានភ្ជាប់រួចរាល់ ✅)\n"
        "⏰ *របាយការណ៍ស្វ័យប្រវត្តិ*: ផ្ញើជូនរៀងរាល់ម៉ោង *10:40 PM (22:40)* យប់\n\n"
        "👇 *លោកអ្នកអាចចុចលើ Button នៅផ្នែកខាងក្រោមនៃអេក្រង់ Telegram ដើម្បីប្រើប្រាស់*:"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "❓ *សៀវភៅណែនាំប្រើប្រាស់ Speed Queen Bot (Clean24 Veng Sreng)*\n\n"
        "1. **របាយការណ៍ស្ថានភាព**: ចុចលើ Button `📊 ស្ថានភាពម៉ាស៊ីន` ដើម្បីមើលស្ថានភាព W1 ដល់ D10។\n"
        "2. **របាយការណ៍ចំណូល**: ចុចលើ Button `💰 របាយការណ៍ចំណូល` ដើម្បីទាញយកចំណូលសរុបប្រចាំថ្ងៃផ្ទាល់ពី Speed Queen Insights។\n"
        "3. **សាកល្បងសារ START/END**: ផ្ញើសារ `/teststart` ឬ `/testend` ដើម្បីសាកល្បងសារជូនដំណឹងស្វ័យប្រវត្តិ។\n"
        "4. **ការជូនដំណឹងស្វ័យប្រវត្តិប្រចាំថ្ងៃ**: ប្រព័ន្ធផ្ញើរបាយការណ៍ចំណូលស្វ័យប្រវត្តិនាតាមម៉ោង **10:40 PM** រៀងរាល់យប់។"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def send_status_response(update: Update) -> None:
    sids = Config.TRACKED_MACHINE_SIDS or ["1517969"]
    cards = []
    for sid in sids:
        summary = sq_client.get_machine_summary(sid, room_id="23546")
        cards.append(build_location_status_card(summary))

    reply_text = "\n\n---\n\n".join(cards)
    await update.message.reply_text(reply_text, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_status_response(update)


async def teststart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    tracker.add_subscriber(chat_id)
    alert_msg = (
        "🤖 *ការជូនដំណឹងស្វ័យប្រវត្តិ*\n\n"
        "🚀 *ម៉ាស៊ីនចាប់ផ្តើមដំណើរការ! (Test Alert)*\n"
        "🧺 *Clean24 Veng Sreng*\n"
        "🔢 *ម៉ាស៊ីន៖* W1 (9kg)\n"
        "🔵 *ស្ថានភាព៖* កំពុងដំណើរការ\n"
        "⏱️ 35 នាទី"
    )
    await update.message.reply_text(alert_msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def testend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    tracker.add_subscriber(chat_id)
    alert_msg = (
        "🤖 *ការជូនដំណឹងស្វ័យប្រវត្តិ*\n\n"
        "🎉 *ម៉ាស៊ីនបោក/សម្ងួតរួចរាល់! (Test Alert)*\n"
        "🧺 *Clean24 Veng Sreng*\n"
        "🔢 *ម៉ាស៊ីន៖* W1 (9kg)\n"
        "🟢 *ស្ថានភាព៖* ទំនេរ (រួចរាល់)"
    )
    await update.message.reply_text(alert_msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def send_revenue_report_card(app: Application, chat_ids: Set[str], update: Update = None) -> None:
    rev_report = sq_client.get_live_daily_revenue_report(room_id="23546")
    if rev_report.get("error"):
        logger.error("Error generating daily revenue report card")
        return

    today_raw = rev_report.get("date", datetime.now().strftime("%Y-%m-%d"))
    khmer_date_str = format_khmer_date(today_raw)

    tot_rev = rev_report.get("total_revenue", 0)
    tot_usd = tot_rev / 4000.0
    tot_turns = rev_report.get("total_turns", 0)

    msg = (
        f"🤖 *ការជូនដំណឹងស្វ័យប្រវត្តិ*\n\n"
        f"📊 *របាយការណ៍ហិរញ្ញវត្ថុប្រចាំថ្ងៃ*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧺 *ហាង៖* Clean24 Veng Sreng\n"
        f"📅 *ថ្ងៃទី៖* {khmer_date_str}\n\n"
        f"💰 *ចំណូលសរុប៖* {tot_rev:,}៛\n"
        f"💲 *ស្មើប្រហែល៖* ${tot_usd:.2f} USD\n"
        f"🔄 *ចំនួនជុំសរុប៖* {tot_turns}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    target_chats = tracker.subscribed_chats if not update else {str(update.effective_chat.id)}
    if update:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())
    else:
        for chat_id in list(target_chats):
            try:
                await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())
                logger.info(f"Scheduled 10:40 PM revenue report sent successfully to chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send 10:40 PM revenue report to chat {chat_id}: {e}")


async def revenue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_revenue_report_card(context.application, set(), update=update)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_monitoring_check(context.application)
    await send_status_response(update)


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    tracker.add_subscriber(chat_id)
    await update.message.reply_text("✅ *បានភ្ជាប់រួចរាល់!* អ្នកនឹងទទួលបានសារជូនដំណឹងភ្លាមៗរៀងរាល់ម៉ោង *10:40 PM* យប់ និងពេលម៉ាស៊ីនបោក/សម្ងួតរួចរាល់។", parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    tracker.remove_subscriber(chat_id)
    await update.message.reply_text("🔕 *បានបិទការជូនដំណឹង!* ផ្អាកការផ្ញើសារជូនដំណឹងស្វ័យប្រវត្តិសម្រាប់ Chat នេះ។", parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def machines_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "🧺 *បញ្ជីម៉ាស៊ីន Clean24 Veng Sreng (១០ គ្រឿង)*:\n"
        "• `W1` - Washer Extractor 9 kg\n"
        "• `W2` - Washer Extractor 14 kg\n"
        "• `W3` - Washer Extractor 14 kg\n"
        "• `W4` - Washer Extractor 14 kg\n"
        "• `W5` - Washer Extractor 14 kg\n"
        "• `W6` - Washer Extractor 18 kg\n"
        "• `D7` - Tumbler 14 kg Stack\n"
        "• `D8` - Tumbler 14 kg Stack\n"
        "• `D9` - Tumbler 14 kg Stack\n"
        "• `D10` - Tumbler 14 kg Stack"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_persistent_reply_keyboard())


async def reply_text_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if text == "📊 ស្ថានភាពម៉ាស៊ីន":
        await send_status_response(update)
    elif text == "💰 របាយការណ៍ចំណូល":
        await send_revenue_report_card(context.application, set(), update=update)
    elif text == "🔄 ពិនិត្យភ្លាមៗ":
        await run_monitoring_check(context.application)
        await send_status_response(update)
    elif text == "🧺 បញ្ជីម៉ាស៊ីន W1-D10":
        await machines_command(update, context)
    elif text == "❓ សៀវភៅណែនាំ":
        await help_command(update, context)


async def run_monitoring_check(app: Application) -> None:
    sids = Config.TRACKED_MACHINE_SIDS or ["1517969"]

    for sid in sids:
        loc_data = sq_client.get_location_and_machines(sid, room_id="23546")
        if loc_data.get("error"):
            continue

        loc_name = loc_data.get("location_name", "Clean24 Veng Sreng")
        machines = loc_data.get("machines", {})

        for m_id, m_info in machines.items():
            meta = MACHINE_METADATA.get(m_id, {"name": f"W{m_id}", "capacity": "14kg", "type": "Washer/Dryer"})
            m_name = meta["name"]
            m_cap = meta["capacity"]
            m_display = f"{m_name} ({m_cap})"

            status = str(m_info.get("statusId", "UNKNOWN")).upper()
            rem_sec = m_info.get("remainingSeconds", 0)
            rem_min = rem_sec // 60 if (rem_sec and rem_sec < 1800) else 0

            state_payload = {
                "status": status,
                "remaining_minutes": rem_min,
                "name": m_display,
                "door_open": m_info.get("isDoorOpen", False)
            }

            has_changed, old_data, new_data = tracker.update_machine_state(f"23546_{m_id}", state_payload)

            if has_changed and tracker.subscribed_chats:
                old_status = old_data.get("status") if old_data else None
                new_status = new_data.get("status")

                running_statuses = ["IN_USE", "RUNNING", "WASHING", "DRYING"]
                finished_statuses = ["AVAILABLE", "IDLE", "COMPLETE", "FINISHED", "END_OF_CYCLE"]

                is_running = new_status in running_statuses
                was_running = old_status in running_statuses
                is_finished = new_status in finished_statuses

                alert_msg = None

                # 1. STRICT START ALERT
                if is_running and not was_running:
                    time_info = f"⏱️ {rem_min} នាទី" if rem_min > 0 else "⏱️ កំពុងដំណើរការ"
                    alert_msg = (
                        f"🤖 *ការជូនដំណឹងស្វ័យប្រវត្តិ*\n\n"
                        f"🚀 *ម៉ាស៊ីនចាប់ផ្តើមដំណើរការ!*\n"
                        f"🧺 *{loc_name}*\n"
                        f"🔢 *ម៉ាស៊ីន៖* {m_display}\n"
                        f"🔵 *ស្ថានភាព៖* កំពុងដំណើរការ\n"
                        f"{time_info}"
                    )
                # 2. STRICT END / FINISH ALERT
                elif is_finished and was_running:
                    alert_msg = (
                        f"🤖 *ការជូនដំណឹងស្វ័យប្រវត្តិ*\n\n"
                        f"🎉 *ម៉ាស៊ីនបោក/សម្ងួតរួចរាល់!*\n"
                        f"🧺 *{loc_name}*\n"
                        f"🔢 *ម៉ាស៊ីន៖* {m_display}\n"
                        f"🟢 *ស្ថានភាព៖* ទំនេរ (រួចរាល់)"
                    )

                if alert_msg:
                    for chat_id in list(tracker.subscribed_chats):
                        try:
                            await app.bot.send_message(
                                chat_id=chat_id,
                                text=alert_msg,
                                parse_mode="Markdown",
                                disable_web_page_preview=True,
                                reply_markup=get_persistent_reply_keyboard()
                            )
                            logger.info(f"Strict START/END alert sent for {m_display} to chat {chat_id}")
                        except Exception as e:
                            logger.error(f"Failed to send alert to chat {chat_id}: {e}")


async def periodic_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_monitoring_check(context.application)


async def daily_scheduled_revenue_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Executing scheduled 10:40 PM daily revenue report job...")
    await send_revenue_report_card(context.application, tracker.subscribed_chats)


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("status", "📊 ពិនិត្យស្ថានភាពម៉ាស៊ីន (W1 - D10)"),
        BotCommand("revenue", "💰 របាយការណ៍ចំណូលសរុបប្រចាំថ្ងៃ"),
        BotCommand("check", "🔄 ពិនិត្យទិន្នន័យភ្លាមៗ"),
        BotCommand("machines", "🧺 បញ្ជីម៉ាស៊ីន (W1 - D10)"),
        BotCommand("teststart", "🚀 សាកល្បងផ្ញើសារ START Alert"),
        BotCommand("testend", "🎉 សាកល្បងផ្ញើសារ END Alert"),
        BotCommand("help", "❓ សៀវភៅណែនាំប្រើប្រាស់"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Telegram Bot Menu commands configured successfully.")


def main():
    if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_BOT_TOKEN missing in .env")
        sys.exit(1)


    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Add Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("revenue", revenue_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("machines", machines_command))
    app.add_handler(CommandHandler("teststart", teststart_command))
    app.add_handler(CommandHandler("testend", testend_command))

    # Add Text Button Message Handler (Persistent Reply Keyboard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_text_button_handler))

    # Add periodic status check job (every 60s)
    job_queue: JobQueue = app.job_queue
    if job_queue:
        job_queue.run_repeating(periodic_check_job, interval=Config.CHECK_INTERVAL_SECONDS, first=5)

        # Schedule daily revenue report at 10:40 PM (22:40) Phnom Penh Local Time
        local_tz = pytz.timezone("Asia/Phnom_Penh")
        report_time = time(hour=22, minute=40, second=0, tzinfo=local_tz)
        job_queue.run_daily(daily_scheduled_revenue_job, time=report_time)
        print(f"⏰ Daily 10:40 PM Revenue Report scheduled for time: {report_time}")

    print("🚀 Speed Queen Insights Telegram Bot (with /teststart & /testend commands) is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
