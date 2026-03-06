#!/usr/bin/env python3
import os
import sys
import time
import signal
from logger import logger, setup_logger
import config
import telegram
import handlers as bot_handlers

def signal_handler(sig, frame):
    logger.info("Shutting down bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class RepoBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            sys.exit(1)
        
        self.bot = telegram.TelegramBot(self.token)
        self.handlers = bot_handlers.BotHandlers(self.bot)
        self.offset = None
        logger.info("Bot initialized successfully")
    
    def run(self):
        logger.info("Starting bot polling...")
        
        while True:
            try:
                updates = self.bot.get_updates(offset=self.offset, timeout=30)
                
                for update in updates:
                    try:
                        self.offset = update["update_id"] + 1
                        self.process_update(update)
                    except Exception as e:
                        logger.error(f"Error processing update: {e}")
                        continue
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)
    
    def process_update(self, update: dict) -> None:
        chat_id = None
        message = update.get("message")
        
        if message:
            chat_id = message["chat"]["id"]
            logger.info(f"Message from {chat_id}: {message.get('text', '[non-text]')}")
            
            # Handle text messages
            if message.get("text"):
                self.handlers.process_message(chat_id, message)
            
            # Handle documents
            elif message.get("document"):
                self.handlers.process_document(chat_id, message["document"])
            
            # Handle photos
            elif message.get("photo"):
                self.handlers.process_photo(chat_id, message["photo"])
        
        # Handle callback queries
        callback = update.get("callback_query")
        if callback:
            chat_id = callback["chat_instance"]
            data = callback.get("data")
            logger.info(f"Callback from {chat_id}: {data}")
            self.bot.answer_callback(callback["id"])

def main():
    logger.info(f"RepoBot v{config.BOT_VERSION} starting...")
    
    # Verify directories
    logger.info(f"Data dir: {config.DATA_DIR}")
    logger.info(f"Users dir: {config.USERS_DIR}")
    logger.info(f"Temp dir: {config.TMP_DIR}")
    
    # Create bot instance
    bot = RepoBot()
    
    # Run bot
    try:
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
