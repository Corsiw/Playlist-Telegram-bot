import telegram
import json

from typing import Final
from time import strftime, gmtime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, \
    ConversationHandler, CallbackQueryHandler

playlists = {}
info = {}

MAIN, PLAYLIST, ADD, REMOVE, RENAME, CREATE, DELETE = range(7)

MAX_PLAYLISTS: Final = 5
MAIN_PHOTO: Final = 'AgACAgIAAxkDAAIOR2SXbypx7QcAAaBoMCHs9zIFqXez6QACos8xGz8DwEgoHeM0iQMRjAEAAwIAA3MAAy8E'


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if str(update.message.chat.id) not in playlists.keys():
        await update.message.reply_text(
        "Привет, это Music playlists Бот! С моей помощью можно создавать и изменять плейлисты с вашей любимой музыкой!")

        playlists[str(update.message.chat.id)] = {}
        with open("playlists.json", "w") as f:
            json.dump(playlists, f)

        info[str(update.message.chat.id)] = {}
        with open("playlists_info.json", "w") as f:
            json.dump(info, f)

    if "bot_message" in context.user_data.keys():
        try:
            await context.bot.deleteMessage(context.user_data["bot_message"].chat.id,
                                            context.user_data["bot_message"].message_id)
        except telegram.error.BadRequest:
            pass

    context.user_data["bot_message"] = await context.bot.send_photo(update.message.chat.id, MAIN_PHOTO, ".", reply_markup=telegram.InlineKeyboardMarkup(inline_keyboard=[]))

    await build_start_menu(update, context)
    return MAIN


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, это Music playlists Бот! С моей помощью можно создавать и изменять плейлисты с вашей любимой музыкой!")


# Starting menu
async def build_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    bot_message = context.user_data["bot_message"]

    keyboard = [[telegram.InlineKeyboardButton(pl, callback_data=pl) for pl in playlists[str(bot_message.chat.id)]],
                [telegram.InlineKeyboardButton(f"Новый плейлист", callback_data="NEW_PLAYLIST")]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_caption(bot_message.chat.id,
                                           bot_message.message_id,
                                           caption="")
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)

    return MAIN

#
#
#
#
#
# ДРУГОЙ ФОРМАТ ДЛЯ КАРТИНКИ
#

async def start_menu_button(update: Update, context: CallbackContext):

    bot_message = context.user_data["bot_message"]

    if update.callback_query.data == "NEW_PLAYLIST":
        if len(playlists[str(bot_message.chat.id)]) >= MAX_PLAYLISTS:
            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Вы достигли лимита")
            return MAIN

        else:
            keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Назовите плейлист",)
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            return CREATE

    elif update.callback_query.data in playlists[str(bot_message.chat.id)]:
        await context.bot.edit_message_caption(bot_message.chat.id,
                                               bot_message.message_id,
                                               caption=f"{update.callback_query.data}")
        context.user_data['cur_playlist_name'] = update.callback_query.data

        await build_playlist_menu(update, context)
        return PLAYLIST


async def build_playlist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["cur_added"] = 0
    bot_message = context.user_data["bot_message"]

    keyboard = [
        [telegram.InlineKeyboardButton("Список", callback_data=1),
         telegram.InlineKeyboardButton("Добавить", callback_data=2),
         telegram.InlineKeyboardButton("Удалить", callback_data=3)],
        [telegram.InlineKeyboardButton("Переименовать", callback_data=4),
         telegram.InlineKeyboardButton("УДАЛИТЬ ПЛЕЙЛИСТ", callback_data=5),
         telegram.InlineKeyboardButton("Назад", callback_data=0)]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_caption(bot_message.chat.id,
                                           bot_message.message_id,
                                           caption=context.user_data['cur_playlist_name'] + " " +
                                                   str(info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']].get("track_number", 0)) + " " +
                                                   strftime("%H:%M:%S", gmtime(info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']].get("duration", 0))))
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)

    return PLAYLIST


async def playlist_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.callback_query.data
    bot_message = context.user_data["bot_message"]

    match action:
        case "1":
            for track in playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]:
                await context.bot.send_audio(chat_id=bot_message.chat.id,
                                             audio=playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']][track][0])

        case "2":
            keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data="0")]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Отправьте треки для добавления",)
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            return ADD

        case "3":
            tracks = [telegram.InlineKeyboardButton(track, callback_data=track) for track in playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]]

            keyboard = [tracks[i:i+3] for i in range(0, len(tracks), 3)]
            keyboard.append([telegram.InlineKeyboardButton("Назад", callback_data="0")])
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            return REMOVE

        case "4":
            keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data="0")]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Введите новое название плейлиста", )
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            return RENAME

        case "5":
            keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data="0")]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_caption(
                bot_message.chat.id,
                bot_message.message_id,
                caption=f"Подтвердите удаление плейлиста {context.user_data['cur_playlist_name']}."
                        f" Введите его полное название")
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            return DELETE

        case "0":
            await build_start_menu(update, context)
            return MAIN


async def playlist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    bot_message = context.user_data["bot_message"]

    if update.callback_query and update.callback_query.data == "0":

        with open("playlists.json", "w") as f:
            json.dump(playlists, f)
        with open("playlists_info.json", "w") as f:
            json.dump(info, f)

        await build_playlist_menu(update, context)
        return PLAYLIST

    full_title = " - "
    if update.message.audio.performer:
        full_title = update.message.audio.performer + full_title
    if update.message.audio.title:
        full_title = full_title + update.message.audio.title

    keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    # Проверка на допустимость названия в 64 байта
    if len(full_title.encode('utf-8')) > 64:
        full_title = full_title[0:20] + "..." + full_title[-20:0]

    # Проверка на наличие трека в плейлисте
    if full_title in playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]:

        await context.bot.edit_message_caption(bot_message.chat.id,
                                               bot_message.message_id,
                                               caption=f"Добавлено треков: {context.user_data['cur_added']}")
        await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                    bot_message.message_id,
                                                    reply_markup=reply_markup)
        return ADD

    playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']][full_title] = (update.message.audio.file_id, update.message.audio.duration)

    info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]["duration"] += update.message.audio.duration
    info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]["track_number"] += 1

    context.user_data["cur_added"] += 1

    await context.bot.edit_message_caption(bot_message.chat.id,
                                           bot_message.message_id,
                                           caption=f"Добавлено треков: {context.user_data['cur_added']}")
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)
    return ADD


async def playlist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query.data == "0":

        with open("playlists.json", "w") as f:
            json.dump(playlists, f)
        with open("playlists_info.json", "w") as f:
            json.dump(info, f)

        await build_playlist_menu(update, context)
        return PLAYLIST

    bot_message = context.user_data["bot_message"]

    if update.callback_query.data in playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]:

        info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]["duration"] -= playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']][update.callback_query.data][1]
        info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]["track_number"] -= 1

        del playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']][update.callback_query.data]

    tracks = [telegram.InlineKeyboardButton(track, callback_data=track)
              for track in
              playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]]
    keyboard = [tracks[i:i + 3] for i in range(0, len(tracks), 3)]
    keyboard.append([telegram.InlineKeyboardButton("Назад", callback_data="0")])
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_caption(bot_message.chat.id,
                                           bot_message.message_id,
                                           caption="")
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)
    return REMOVE


async def playlist_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query and update.callback_query.data == "0":
        await build_playlist_menu(update, context)
        return PLAYLIST

    new_name = update.message.text
    bot_message = context.user_data["bot_message"]

    keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    if new_name not in playlists[str(bot_message.chat.id)]:

        playlists[str(bot_message.chat.id)][new_name] = playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]
        del playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]
        with open("playlists.json", "w") as f:
            json.dump(playlists, f)

        info[str(bot_message.chat.id)][new_name] = info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]
        del info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]
        with open("playlists_info.json", "w") as f:
            json.dump(info, f)

        context.user_data['cur_playlist_name'] = new_name

        await context.bot.edit_message_caption(bot_message.chat.id,
                                               bot_message.message_id,
                                               caption=f"{new_name}")
        await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                    bot_message.message_id,
                                                    reply_markup=reply_markup)
        return RENAME

    else:

        await context.bot.edit_message_caption(bot_message.chat.id,
                                               bot_message.message_id,
                                               caption=f"Плейлист c именем {new_name} уже существует")
        await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                    bot_message.message_id,
                                                    reply_markup=reply_markup)
        return RENAME


async def playlist_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query and update.callback_query.data == "0":
        await build_playlist_menu(update, context)
        return PLAYLIST

    if update.message.text == context.user_data['cur_playlist_name']:

        bot_message = context.user_data["bot_message"]

        del playlists[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]
        with open("playlists.json", "w") as f:
            json.dump(playlists, f)

        del info[str(bot_message.chat.id)][context.user_data['cur_playlist_name']]
        with open("playlists_info.json", "w") as f:
            json.dump(info, f)

        await build_start_menu(update, context)
        return MAIN

    else:
        await build_playlist_menu(update, context)
        return PLAYLIST


async def playlist_create(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query and update.callback_query.data == "0":
        await build_start_menu(update, context)
        return MAIN

    bot_message = context.user_data["bot_message"]
    name = update.message.text

    if name not in playlists[str(bot_message.chat.id)]:

        playlists[str(bot_message.chat.id)][name] = {}
        with open("playlists.json", "w") as f:
            json.dump(playlists, f)

        info[str(bot_message.chat.id)][name] = {"duration": 0, "track_number": 0}
        with open("playlists_info.json", "w") as f:
            json.dump(info, f)


    else:
        keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        await context.bot.edit_message_caption(bot_message.chat.id,
                                               bot_message.message_id,
                                               caption=f"{name} уже существует")
        await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                    bot_message.message_id,
                                                    reply_markup=reply_markup)
        return CREATE

    await build_start_menu(update, context)
    return MAIN


if __name__ == "__main__":
    application = Application.builder().token("6059715082:AAEBO0Gp05BigDY2IqyTAeXRkrvwKRzovMU").build()

    with open("playlists.json", "r") as f:
        playlists = json.load(f)
    with open("playlists_info.json", "r") as f:
        info = json.load(f)

    main_handler = ConversationHandler(
        allow_reentry=True,
        entry_points=[CommandHandler("start", start_command)],
        states={
            MAIN: [
                CallbackQueryHandler(start_menu_button)
            ],

            PLAYLIST: [
                CallbackQueryHandler(playlist_button)
            ],

            ADD: [
                CallbackQueryHandler(playlist_add),
                MessageHandler(filters.AUDIO, playlist_add)
            ],

            REMOVE: [
                CallbackQueryHandler(playlist_remove)
            ],

            RENAME: [
                CallbackQueryHandler(playlist_rename),
                MessageHandler(filters.TEXT, playlist_rename)
            ],

            DELETE: [
                CallbackQueryHandler(playlist_delete),
                MessageHandler(filters.TEXT, playlist_delete)
            ],

            CREATE: [
                CallbackQueryHandler(playlist_create),
                MessageHandler(filters.TEXT, playlist_create)
            ]
        },
        fallbacks=[]
    )
    application.add_handler(main_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)
