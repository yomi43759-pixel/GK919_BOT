import asyncio
import logging
import os
import random

import aiohttp
import feedparser
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# ------------------------------------------------------------------
# Configuration — Render-aware
# ------------------------------------------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# Render provides the full https://… URL automatically
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

WEBHOOK_PATH = "/webhook"
# If RENDER_EXTERNAL_URL is present, build the full webhook URL
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}" if RENDER_EXTERNAL_URL else None

# ------------------------------------------------------------------
# Educational content (unchanged from your Railway version)
# ------------------------------------------------------------------
ABOUT_TEXT = """
📊 Sharing educational trading content only

📚 Educational content only

This bot is designed to help you learn about forex trading. It does **not** provide financial advice, trading signals, or recommendations to buy or sell any instrument.

Use /news for latest forex headlines (educational context).
Use /lessons for quick educational tips.
Use /disclaimer for the full risk disclaimer.
"""

LESSONS = [
    "📚 **Lesson: What is a pip?** A pip is the smallest standardised price move in a currency pair. For most pairs, one pip is 0.0001; for JPY pairs, it is 0.01. Understanding pips helps you measure risk and reward consistently.",
    "📚 **Lesson: Risk management is key.** Professional traders often risk only 1–2 % of their account per trade. This keeps a losing streak from wiping out the account and is a foundational concept in forex education.",
    "📚 **Lesson: Support and resistance.** These are price zones where the market has historically reversed. They are not magic lines but areas of supply and demand. Learning to identify them is part of technical analysis education.",
    "📚 **Lesson: What is leverage?** Leverage lets you control a large position with a small deposit, but it magnifies both profits **and losses**. Education about leverage is critical because misuse is a leading cause of retail trader losses.",
    "📚 **Lesson: Major forex sessions.** Sydney, Tokyo, London, and New York sessions overlap at different times. Volatility often increases during the London–New York overlap. Knowing session times helps you understand market behaviour.",
]

DISCLAIMER = """
⚠️ **Disclaimer — Educational content only**

This bot provides educational material about forex trading. It does **not** offer financial advice, trading signals, or recommendations to buy or sell any financial instrument. Trading forex involves significant risk of loss. Past performance is not indicative of future results. Always do your own research and consult a licensed financial advisor before making any trading decisions.
"""

# ------------------------------------------------------------------
# Router / handlers (unchanged)
# ------------------------------------------------------------------
router = Router()


@router.message(Command("start", "about"))
async def cmd_start(message: types.Message):
    await message.answer(ABOUT_TEXT)


@router.message(Command("disclaimer"))
async def cmd_disclaimer(message: types.Message):
    await message.answer(DISCLAIMER)


@router.message(Command("lessons"))
async def cmd_lessons(message: types.Message):
    lesson = random.choice(LESSONS)
    await message.answer(f"{lesson}\n\n{DISCLAIMER}")


@router.message(Command("news"))
async def cmd_news(message: types.Message):
    feed_url = "https://www.fxstreet.com/rss/news"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(feed_url, timeout=10) as resp:
                resp.raise_for_status()
                raw = await resp.text()
    except Exception:
        logging.exception("Failed to fetch forex news")
        await message.answer(
            "⚠️ Could not fetch news right now. Please try again later.\n\n"
            + DISCLAIMER
        )
        return

    feed = feedparser.parse(raw)
    entries = feed.entries[:5]

    if not entries:
        await message.answer("No headlines available at the moment.\n\n" + DISCLAIMER)
        return

    news_text = "📰 **Latest Forex Headlines — Educational Context**\n\n"
    for entry in entries:
        news_text += f"• {entry.title}\n"
    news_text += f"\n{DISCLAIMER}"

    await message.answer(news_text)


# ------------------------------------------------------------------
# Health check for Render
# ------------------------------------------------------------------
async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


# ------------------------------------------------------------------
# Startup / webhook registration
# ------------------------------------------------------------------
async def on_startup(bot: Bot):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info("Webhook set to %s", WEBHOOK_URL)
    else:
        logging.warning(
            "RENDER_EXTERNAL_URL not found. Webhook will NOT be registered. "
            "Are you running outside Render?"
        )


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    app = web.Application()
    app.router.add_get("/healthcheck", health_check)  # Render-friendly path

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    async def run():
        await on_startup(bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
        await site.start()
        logging.info("Server running on port %s", PORT)

    asyncio.run(run())


if __name__ == "__main__":
    main()
