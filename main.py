import telegram
import psycopg2

from typing import Final
from time import strftime, gmtime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, \
    ConversationHandler, CallbackQueryHandler

MAIN, PLAYLIST, ADD, REMOVE, RENAME, CREATE, DELETE = range(7)

MAX_PLAYLISTS: Final = 10
MAIN_PHOTO: Final = 'AgACAgIAAxkDAAIOR2SXbypx7QcAAaBoMCHs9zIFqXez6QACos8xGz8DwEgoHeM0iQMRjAEAAwIAA3MAAy8E'


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "bot_message" in context.user_data.keys():
        try:
            await context.bot.deleteMessage(context.user_data["bot_message"].chat.id,
                                            context.user_data["bot_message"].message_id)
        except telegram.error.BadRequest:
            pass
    else:
        await update.message.reply_text(
            "Привет, это Music playlists Бот! С моей помощью можно создавать и изменять плейлисты с вашей любимой музыкой!")

    context.user_data["bot_message"] = await context.bot.send_photo(update.message.chat.id, MAIN_PHOTO, ".", reply_markup=telegram.InlineKeyboardMarkup(inline_keyboard=[]))

    await build_start_menu(update, context)
    return MAIN


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, это Music playlists Бот! С моей помощью можно создавать и изменять плейлисты с вашей любимой музыкой!")


async def build_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_message = context.user_data["bot_message"]

    sql = f"""SELECT name
    FROM public.playlists
    WHERE chat_id = '{bot_message.chat.id}'
    ORDER BY name ASC"""

    keys = [telegram.InlineKeyboardButton(pl[0], callback_data=pl[0]) for pl in await db_get(sql)]
    keyboard = [keys[i:i + 2] for i in range(0, len(keys), 2)]
    keyboard.append([telegram.InlineKeyboardButton(f"Новый плейлист", callback_data="NEW_PLAYLIST")])
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_caption(bot_message.chat.id,
                                           bot_message.message_id,
                                           caption="")
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)

    return MAIN


# TODO: Другой формат картинки

async def start_menu_button(update: Update, context: CallbackContext):
    bot_message = context.user_data["bot_message"]

    if update.callback_query.data == "0":
        await build_start_menu(update, context)
        return MAIN

    elif update.callback_query.data == "NEW_PLAYLIST":
        sql = f"""SELECT name
        FROM public.playlists
        WHERE chat_id = '{bot_message.chat.id}'"""

        keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        if len(await db_get(sql)) >= MAX_PLAYLISTS:
            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Вы достигли лимита")
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)

        else:
            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Назовите плейлист")
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            return CREATE

    else:
        await context.bot.edit_message_caption(bot_message.chat.id,
                                               bot_message.message_id,
                                               caption=f"{update.callback_query.data}")

        r = await db_get(f"""SELECT id
        FROM public.playlists
        WHERE name = '{update.callback_query.data}'
        """)
        context.user_data['cur_playlist_name'] = update.callback_query.data
        context.user_data['cur_playlist_id'] = r[0][0]

        await build_playlist_menu(update, context)
        return PLAYLIST


async def build_playlist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cur_added"] = 0
    bot_message = context.user_data["bot_message"]

    response = await db_get(f"""SELECT duration
    FROM playlists_songs LEFT JOIN songs ON playlists_songs.song_id = songs.id
    WHERE playlist_id = '{context.user_data['cur_playlist_id']}'""")
    duration = sum([r[0] for r in response])
    track_num = len(response)

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
                                                   str(track_num) + " " +
                                                   strftime("%H:%M:%S", gmtime(duration)))
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)

    return PLAYLIST


async def playlist_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.callback_query.data
    bot_message = context.user_data["bot_message"]

    match action:
        case "1":
            sql = f"""SELECT file_id
            FROM songs, playlists_songs
            WHERE songs.id = playlists_songs.song_id AND playlists_songs.playlist_id = {context.user_data['cur_playlist_id']}
            """
            for track in await db_get(sql):
                await context.bot.send_audio(chat_id=bot_message.chat.id,
                                             audio=track[0])

        case "2":
            keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data="0")]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Отправьте треки для добавления", )
            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            context.user_data["songs_to_add"] = []
            return ADD

        case "3":
            sql = f"""SELECT name, author, song_id
            FROM songs, playlists_songs
            WHERE songs.id = playlists_songs.song_id AND playlists_songs.playlist_id = {context.user_data['cur_playlist_id']}
            """
            tracks = []
            for track in await db_get(sql):
                text = f"{track[1]} - {track[0]}"[:30]
                tracks.append(telegram.InlineKeyboardButton(text, callback_data=track[2]))

            keyboard = [tracks[i:i + 2] for i in range(0, len(tracks), 2)]
            keyboard.append([telegram.InlineKeyboardButton("Назад", callback_data="0")])
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                        bot_message.message_id,
                                                        reply_markup=reply_markup)
            context.user_data["songs_to_remove"] = []
            return REMOVE

        case "4":
            keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data="0")]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
            await context.bot.edit_message_caption(bot_message.chat.id,
                                                   bot_message.message_id,
                                                   caption="Введите новое название плейлиста")
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
        sql = []
        for song in context.user_data["songs_to_add"]:
            if song.performer:
                author = song.performer
            else:
                author = "Unknown"
            if song.title:
                name = song.title
            else:
                name = "Unknown"

            sql.append(f"SELECT song_add({context.user_data['cur_playlist_id']}, '{song.file_id}', '{song.file_unique_id}', '{name}', '{author}', {song.duration})")
        context.user_data.pop("songs_to_add", None)

        if sql:
            await db_set(";\n".join(sql))
            pg.commit()

        await build_playlist_menu(update, context)
        return PLAYLIST

    keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    context.user_data["songs_to_add"].append(update.message.audio)
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
        sql = []
        for song_id in context.user_data["songs_to_remove"]:
            sql.append(f"""DELETE FROM playlists_songs
            WHERE playlist_id = {context.user_data['cur_playlist_id']} AND song_id = '{song_id}'""")

        context.user_data.pop("songs_to_remove", None)

        if sql:
            await db_set(";\n".join(sql))
            pg.commit()

        await build_playlist_menu(update, context)
        return PLAYLIST

    bot_message = context.user_data["bot_message"]

    # TODO: вся индексация в бд с 1
    context.user_data["songs_to_remove"].append(update.callback_query.data)

    sql = f"""SELECT name, author, song_id
                FROM songs, playlists_songs
                WHERE songs.id = playlists_songs.song_id AND playlists_songs.playlist_id = {context.user_data['cur_playlist_id']}
                """
    tracks = []
    for track in await db_get(sql):
        if str(track[2]) not in context.user_data["songs_to_remove"]:
            text = f"{track[1]} - {track[0]}"[:30]
            tracks.append(telegram.InlineKeyboardButton(text, callback_data=track[2]))

    keyboard = [tracks[i:i + 2] for i in range(0, len(tracks), 2)]
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

    bot_message = context.user_data["bot_message"]

    keyboard = [[telegram.InlineKeyboardButton("Назад", callback_data=0)]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    await db_set(f"""UPDATE playlists
    SET name = '{update.message.text}'
    WHERE id = '{context.user_data['cur_playlist_id']}'""")
    pg.commit()

    context.user_data['cur_playlist_name'] = update.message.text

    await context.bot.edit_message_caption(bot_message.chat.id,
                                           bot_message.message_id,
                                           caption=f"{update.message.text}")
    await context.bot.edit_message_reply_markup(bot_message.chat.id,
                                                bot_message.message_id,
                                                reply_markup=reply_markup)
    return RENAME


async def playlist_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query and update.callback_query.data == "0":
        await build_playlist_menu(update, context)
        return PLAYLIST

    if update.message.text == context.user_data['cur_playlist_name']:

        await db_set(f"""DELETE FROM playlists_songs
        WHERE playlist_id = {context.user_data['cur_playlist_id']};
        DELETE FROM playlists
        WHERE id = {context.user_data['cur_playlist_id']}""")
        pg.commit()

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

    await db_set(f"""INSERT INTO playlists(id, name, chat_id)
                VALUES(nextval('playlists_serial'), '{update.message.text}', '{bot_message.chat.id}')""")
    pg.commit()

    await build_start_menu(update, context)
    return MAIN


async def db_get(sql):
    with pg.cursor() as cr:
        cr.execute(sql)
        return cr.fetchall()


async def db_set(sql):
    with pg.cursor() as cr:
        cr.execute(sql)
        # pg.commit()
        # return cr.fetchone()


if __name__ == "__main__":
    # TODO: УБРАТЬ ТОКЕН
    application = Application.builder().token("6059715082:AAEBO0Gp05BigDY2IqyTAeXRkrvwKRzovMU").build()

    # TODO: Connection pulling
    # TODO: УБРАТЬ КОНФИГ
    pg = psycopg2.connect("""
        host=localhost
        dbname=postgres
        user=postgres
        password=postgres
        port=5432
    """)

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
