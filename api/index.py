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

app = Flask(__name__)

# WSGI Middleware to fix Vercel routing path issue by extracting the original request path from the 'path' query parameter or headers
class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        from urllib.parse import parse_qs
        query_string = environ.get("QUERY_STRING", "")
        params = parse_qs(query_string, keep_blank_values=True)
        path_list = params.get("path")
        if path_list:
            original_path = path_list[0]
            if not original_path.startswith("/"):
                original_path = "/" + original_path
            environ["PATH_INFO"] = original_path
        else:
            matched_path = environ.get("HTTP_X_MATCHED_PATH")
            if matched_path:
                environ["PATH_INFO"] = matched_path
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

def make_bot_app():
    bot_app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
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
    return bot_app

# Helper to run async code synchronously in Flask handler threads
def run_async(coro):
    return asyncio.run(coro)

@app.before_request
def debug_request():
    import sys
    print(f"DEBUG REQUEST - Path: {request.path}, Method: {request.method}, Args: {request.args}", file=sys.stderr)
    print(f"DEBUG REQUEST - PATH_INFO: {request.environ.get('PATH_INFO')}, SCRIPT_NAME: {request.environ.get('SCRIPT_NAME')}", file=sys.stderr)

@app.route("/", methods=["GET"])
def home():
    from sq_client import MACHINE_METADATA
    
    db_mode = "Vercel KV (Cloud Redis) ☁️" if tracker.kv.enabled else "Local JSON Files 📂"
    
    avail_count = 0
    running_count = 0
    oos_count = 0
    unknown_count = 0
    
    machine_cards = []
    sorted_ids = sorted(MACHINE_METADATA.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))
    
    for m_id in sorted_ids:
        meta = MACHINE_METADATA[m_id]
        state = tracker.states.get(f"23546_{m_id}", {})
        
        status = state.get("status", "UNKNOWN").upper()
        rem_min = state.get("remaining_minutes", 0)
        door_open = state.get("door_open", False)
        
        name = meta["name"]
        capacity = meta["capacity"]
        m_type = "Washer" if "Washer" in meta["type"] else "Dryer"
        
        if status in ["RUNNING", "IN_USE", "WASHING", "DRYING"]:
            status_kh = "កំពុងដំណើរការ"
            status_color = "blue"
            status_eng = "RUNNING"
            running_count += 1
        elif status in ["ERROR", "UNAVAILABLE", "OUT_OF_SERVICE", "FAULT"]:
            status_kh = "ខូច"
            status_color = "red"
            status_eng = "OUT OF SERVICE"
            oos_count += 1
        elif status in ["AVAILABLE", "IDLE", "COMPLETE", "FINISHED"]:
            status_kh = "ទំនេរ"
            status_color = "emerald"
            status_eng = "AVAILABLE"
            avail_count += 1
        else:
            status_kh = "មិនស្គាល់"
            status_color = "amber"
            status_eng = "UNKNOWN"
            unknown_count += 1
            
        machine_cards.append({
            "id": m_id,
            "name": name,
            "capacity": capacity,
            "type": m_type,
            "status_eng": status_eng,
            "status_kh": status_kh,
            "status_color": status_color,
            "rem_min": rem_min,
            "door_open": door_open
        })
        
    total_rev = tracker.daily_revenue.get("total_revenue", 0)
    total_turns = tracker.daily_revenue.get("total_turns", 0)
    total_usd = total_rev / 4000.0 if total_rev else 0.0

    # Build machine grid HTML
    grid_html = ""
    for card in machine_cards:
        badge_class = f"badge-{card['status_color']}"
        indicator_class = f"indicator-{card['status_color']}"
        
        time_html = ""
        if card['rem_min'] > 0:
            time_html = f"""
            <div class="time-container">
                <span class="clock-icon">⏱️</span>
                <span class="time-text">{card['rem_min']} នាទី (mins)</span>
            </div>
            """
            
        door_html = ""
        if card['door_open']:
            door_html = """
            <div class="door-badge">🚪 Door Open</div>
            """

        grid_html += f"""
        <div class="machine-card">
            <div class="card-header">
                <div class="machine-name-group">
                    <span class="machine-icon">🧺</span>
                    <h3>{card['name']}</h3>
                </div>
                <div class="status-indicator-group">
                    <span class="status-indicator {indicator_class}"></span>
                    <span class="badge {badge_class}">{card['status_kh']}</span>
                </div>
            </div>
            <div class="card-body">
                <div class="meta-row">
                    <span class="meta-label">ប្រភេទ (Type):</span>
                    <span class="meta-val">{card['type']}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">ចំណុះ (Capacity):</span>
                    <span class="meta-val">{card['capacity']}</span>
                </div>
                {time_html}
                {door_html}
            </div>
        </div>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clean24 Veng Sreng - Bot Monitor</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Siemreap&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-dark: #090d16;
                --bg-card: rgba(17, 24, 39, 0.7);
                --border-color: rgba(255, 255, 255, 0.08);
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
                --color-emerald: #10b981;
                --color-blue: #3b82f6;
                --color-red: #ef4444;
                --color-amber: #f59e0b;
            }}
            
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            
            body {{
                font-family: 'Inter', 'Siemreap', sans-serif;
                background: linear-gradient(135deg, var(--bg-dark) 0%, #111827 100%);
                color: var(--text-main);
                min-height: 100vh;
                padding: 2rem 1.5rem;
                line-height: 1.5;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2.5rem;
                padding-bottom: 1.5rem;
                border-bottom: 1px solid var(--border-color);
                flex-wrap: wrap;
                gap: 1.5rem;
            }}
            
            .header-title h1 {{
                font-size: 2rem;
                font-weight: 700;
                background: linear-gradient(to right, #60a5fa, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.25rem;
            }}
            
            .header-title p {{
                color: var(--text-muted);
                font-size: 0.95rem;
            }}
            
            .db-badge {{
                background: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                font-size: 0.85rem;
                font-weight: 600;
                color: #60a5fa;
            }}
            
            /* KPI Summary Section */
            .kpi-section {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2.5rem;
            }}
            
            .kpi-card {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                backdrop-filter: blur(12px);
                padding: 1.5rem;
                border-radius: 16px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                transition: transform 0.2s;
            }}
            
            .kpi-card:hover {{
                transform: translateY(-2px);
            }}
            
            .kpi-title {{
                color: var(--text-muted);
                font-size: 0.85rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.5rem;
            }}
            
            .kpi-value {{
                font-size: 2.25rem;
                font-weight: 700;
            }}
            
            .kpi-emerald {{ color: var(--color-emerald); }}
            .kpi-blue {{ color: var(--color-blue); }}
            .kpi-red {{ color: var(--color-red); }}
            .kpi-amber {{ color: var(--color-amber); }}
            
            /* Button controls */
            .actions-bar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
                gap: 1rem;
            }}
            
            .btn-refresh {{
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                color: #ffffff;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 12px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.95rem;
                transition: opacity 0.2s, transform 0.1s;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            }}
            
            .btn-refresh:hover {{
                opacity: 0.9;
            }}
            
            .btn-refresh:active {{
                transform: scale(0.98);
            }}
            
            /* Grid */
            .machine-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 1.5rem;
            }}
            
            .machine-card {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 18px;
                overflow: hidden;
                backdrop-filter: blur(12px);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            
            .machine-card:hover {{
                transform: translateY(-4px);
                border-color: rgba(255, 255, 255, 0.15);
                box-shadow: 0 10px 20px rgba(0,0,0,0.3);
            }}
            
            .card-header {{
                padding: 1.25rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border-color);
            }}
            
            .machine-name-group {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            .machine-icon {{
                font-size: 1.25rem;
            }}
            
            .card-header h3 {{
                font-size: 1.15rem;
                font-weight: 600;
            }}
            
            .status-indicator-group {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            .status-indicator {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }}
            
            .indicator-emerald {{
                background-color: var(--color-emerald);
                box-shadow: 0 0 10px var(--color-emerald);
            }}
            
            .indicator-blue {{
                background-color: var(--color-blue);
                box-shadow: 0 0 10px var(--color-blue);
            }}
            
            .indicator-red {{
                background-color: var(--color-red);
                box-shadow: 0 0 10px var(--color-red);
            }}
            
            .indicator-amber {{
                background-color: var(--color-amber);
                box-shadow: 0 0 10px var(--color-amber);
            }}
            
            .badge {{
                padding: 0.25rem 0.5rem;
                font-size: 0.75rem;
                font-weight: 600;
                border-radius: 6px;
            }}
            
            .badge-emerald {{
                background: rgba(16, 185, 129, 0.15);
                color: #34d399;
            }}
            
            .badge-blue {{
                background: rgba(59, 130, 246, 0.15);
                color: #60a5fa;
            }}
            
            .badge-red {{
                background: rgba(239, 68, 68, 0.15);
                color: #f87171;
            }}
            
            .badge-amber {{
                background: rgba(245, 158, 11, 0.15);
                color: #fbbf24;
            }}
            
            .card-body {{
                padding: 1.25rem;
            }}
            
            .meta-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.75rem;
                font-size: 0.9rem;
            }}
            
            .meta-label {{
                color: var(--text-muted);
            }}
            
            .meta-val {{
                font-weight: 600;
            }}
            
            .time-container {{
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 10px;
                padding: 0.5rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 1rem;
                justify-content: center;
            }}
            
            .time-text {{
                font-weight: 600;
                color: #60a5fa;
                font-size: 0.9rem;
            }}
            
            .door-badge {{
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 10px;
                padding: 0.5rem;
                color: #f87171;
                font-weight: 600;
                font-size: 0.85rem;
                margin-top: 0.5rem;
                text-align: center;
            }}
            
            /* Loader spin */
            .spinner {{
                border: 2px solid rgba(255, 255, 255, 0.2);
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border-left-color: #ffffff;
                animation: spin 1s linear infinite;
                display: none;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            @media (max-width: 640px) {{
                body {{
                    padding: 1rem;
                }}
                header {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="header-title">
                    <h1>Clean24 Veng Sreng</h1>
                    <p>Speed Queen Monitoring Dashboard & State Tracker</p>
                </div>
                <div class="db-badge">
                    Database: {db_mode}
                </div>
            </header>
            
            <div class="kpi-section">
                <div class="kpi-card">
                    <span class="kpi-title">ទំនេរ (Available)</span>
                    <span class="kpi-value kpi-emerald">{avail_count}</span>
                </div>
                <div class="kpi-card">
                    <span class="kpi-title">កំពុងដំណើរការ (Running)</span>
                    <span class="kpi-value kpi-blue">{running_count}</span>
                </div>
                <div class="kpi-card">
                    <span class="kpi-title">ខូច (Out of Service)</span>
                    <span class="kpi-value kpi-red">{oos_count}</span>
                </div>
                <div class="kpi-card">
                    <span class="kpi-title">ចំណូលថ្ងៃនេះ (Today's Revenue)</span>
                    <span class="kpi-value kpi-amber">{total_rev:,}៛ (~${total_usd:.2f})</span>
                </div>
            </div>
            
            <div class="actions-bar">
                <h2>ស្ថានភាពម៉ាស៊ីន (Machine Status)</h2>
                <button class="btn-refresh" onclick="triggerCheck()">
                    <span class="spinner" id="spinner"></span>
                    <span id="btn-text">🔄 ពិនិត្យទិន្នន័យភ្លាមៗ (Check Now)</span>
                </button>
            </div>
            
            <div class="machine-grid">
                {grid_html}
            </div>
        </div>
        
        <script>
            function triggerCheck() {{
                const spinner = document.getElementById("spinner");
                const btnText = document.getElementById("btn-text");
                spinner.style.display = "inline-block";
                btnText.textContent = " កំពុងទាញយកទិន្នន័យ (Fetching)...";
                
                fetch("/api/cron/check")
                    .then(response => response.json())
                    .then(data => {{
                        location.reload();
                    }})
                    .catch(err => {{
                        console.error(err);
                        alert("Error triggering status check.");
                        spinner.style.display = "none";
                        btnText.textContent = "🔄 ពិនិត្យទិន្នន័យភ្លាមៗ (Check Now)";
                    }});
            }}
        </script>
    </body>
    </html>
    """
    
    return html_template, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/webhook", methods=["POST"])
def webhook():
    """
    Inbound Webhook endpoint for Telegram updates.
    """
    try:
        update_json = request.get_json(force=True)
        bot_app = make_bot_app()
        
        async def main_task():
            await bot_app.initialize()
            await bot_app.start()
            try:
                await post_init(bot_app)
            except Exception as pe:
                logger.error(f"Error in post_init: {pe}")
            
            update = Update.de_json(update_json, bot_app.bot)
            await bot_app.process_update(update)
            await bot_app.stop()
            await bot_app.shutdown()
            
        run_async(main_task())
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
        bot_app = make_bot_app()
        
        async def main_task():
            await bot_app.initialize()
            await bot_app.start()
            logger.info("Triggering periodic status check via cron...")
            await run_monitoring_check(bot_app)
            await bot_app.stop()
            await bot_app.shutdown()
            
        run_async(main_task())
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
        bot_app = make_bot_app()
        
        async def main_task():
            await bot_app.initialize()
            await bot_app.start()
            logger.info("Triggering daily scheduled revenue card broadcast...")
            await send_revenue_report_card(bot_app, tracker.subscribed_chats)
            await bot_app.stop()
            await bot_app.shutdown()
            
        run_async(main_task())
        return jsonify({"status": "daily revenue report broadcast completed"}), 200
    except Exception as e:
        logger.error(f"Error executing daily scheduled revenue card cron: {e}")
        return jsonify({"error": str(e)}), 500
