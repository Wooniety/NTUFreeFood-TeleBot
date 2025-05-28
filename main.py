import os
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# env stuff
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# states
ASK_LOCATION, ASK_CLEARTIME, ASK_ADDITIONALINFO, ASK_PHOTO, CONFIRMATION = range(5)
EDIT_CHOICE, EDIT_LOCATION, EDIT_CLEARTIME, EDIT_ADDITIONALINFO, EDIT_PHOTO = range(5, 10)

async def set_commands(app) -> None:
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("submit", "Submit a free food sighting")
    ]
    await app.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! This is the NTU Free Food Bot.\nType /submit to submit a free food sighting.")

async def submit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Where is it? (e.g Arc B2 outside TR+15)")
    return ASK_LOCATION

async def ask_clear_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["location"] = update.message.text.strip()
    await update.message.reply_text(f"When will the food be cleared? (e.g. 2pm, Expires 31/2/2025, etc.)")
    return ASK_CLEARTIME

async def ask_additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["clear_time"] = update.message.text.strip()

    keyboard = [[InlineKeyboardButton("Skip", callback_data="skip_additional_info"),]]
    await update.message.reply_text(f"Any additional info? (e.g. halal, bring your own container, etc.)", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_ADDITIONALINFO;

async def store_additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["additional_info"] = update.message.text.strip()
    await update.message.reply_text("Please send a photo of the food.")
    return ASK_PHOTO

async def handle_skip_additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    query.answer()

    context.user_data["additional_info"] = ""
    await query.message.reply_text("Please send a photo of the food.")
    return ASK_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data["photo"] = photo.file_id
        return await show_preview(update, context)
    else:
        await update.message.reply_text("Please send a photo!")
        return ASK_PHOTO

def generate_food_announcement(user_data):
    text = (
        f"Location: {user_data.get('location')}\n"
        f"Clear Time: {user_data.get('clear_time')}\n"
        f"Additional Info: {user_data.get('additional_info', '')}\n"
    )

    return text

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = generate_food_announcement(user_data) + "\n\n Submit this?"

    keyboard = [
        [InlineKeyboardButton("Edit", callback_data="edit")],
        [InlineKeyboardButton("Submit", callback_data="submit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id = update.effective_chat.id,
        photo=user_data.get("photo"),
        caption=text,
        reply_markup=reply_markup
    )

    return CONFIRMATION

async def handle_submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    text = generate_food_announcement(context.user_data)
    await context.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=context.user_data.get("photo"),
        caption=text
    )

    await query.edit_message_caption(caption="Your sighting has been sent to the channel!")
    return ConversationHandler.END

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("Location", callback_data="edit_location")],
        [InlineKeyboardButton("Clear Time", callback_data="edit_cleartime")],
        [InlineKeyboardButton("Additional Info", callback_data="edit_additionalinfo")],
        [InlineKeyboardButton("Photo", callback_data="edit_photo")],
        [InlineKeyboardButton("Done Editing", callback_data="done_editing")]
    ]

    await query.edit_message_text(
        text="What would you like to edit?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EDIT_CHOICE

async def edit_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send the new location.")
    return EDIT_LOCATION

async def store_edited_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["location"] = update.message.text.strip()
    return await show_preview(update, context)

async def edit_clear_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send the new clear time.")
    return EDIT_CLEARTIME

async def store_edited_clear_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["clear_time"] = update.message.text.strip()
    return await show_preview(update, context)

async def edit_additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send the new additional info.")
    return EDIT_ADDITIONALINFO

async def store_edited_additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["additional_info"] = update.message.text.strip()
    return await show_preview(update, context)

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Please send the new photo.")
    return EDIT_PHOTO

async def store_edited_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data["photo"] = photo.file_id
        return await show_preview(update, context)
    else:
        await update.message.reply_text("Please send a valid photo.")
        return EDIT_PHOTO

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("submit", submit_start)],
        states={
            ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_clear_time)],
            ASK_CLEARTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_additional_info)],
            ASK_ADDITIONALINFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, store_additional_info),
                CallbackQueryHandler(handle_skip_additional_info, pattern="skip_additional_info")
            ],
            ASK_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            CONFIRMATION: [
                CallbackQueryHandler(handle_submit, pattern="submit"),
                CallbackQueryHandler(handle_edit, pattern="edit")
            ],

            EDIT_CHOICE: [
                CallbackQueryHandler(edit_location, pattern="edit_location"),
                CallbackQueryHandler(edit_clear_time, pattern="edit_cleartime"),
                CallbackQueryHandler(edit_additional_info, pattern="edit_additionalinfo"),
                CallbackQueryHandler(edit_photo, pattern="edit_photo"),
                CallbackQueryHandler(show_preview, pattern="done_editing")
            ],

            EDIT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_edited_location)],
            EDIT_CLEARTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_edited_clear_time)],
            EDIT_ADDITIONALINFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_edited_additional_info)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, store_edited_photo)]
        },
        fallbacks=[],
        per_chat=True,
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    app.post_init = set_commands

    print("Starting bot...")
    app.run_polling()

if __name__ == "__main__":
    main() 