import os
import telegram
import json
from shutil import rmtree
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, \
    ConversationHandler

MAIN, PLAYLIST, ADD, REMOVE, RENAME, CREATE, DELETE = range(7)

playlists = {}

MAX_PLAYLISTS: Final = 5


# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, это Music playlists Бот! С моей помощью можно создавать и изменять плейлисты с вашей любимой музыкой!")
    keyboard = [[telegram.KeyboardButton("Начать!")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text("Нажмите на кнопку, чтобы начать работу бота", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Доступные команды:")


# Starting menu
async def build_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Удаление информации об имени текущего плейлиста и "странице удаления"
    context.user_data.pop('cur_playlist_name', None)
    # context.user_data.pop("cur_playlist_page", None)

    keyboard = [[telegram.KeyboardButton(pl) for pl in playlists], [telegram.KeyboardButton("Новый плейлист")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите плейлист", reply_markup=reply_markup)
    return MAIN


async def start_menu_button(update: Update, context: CallbackContext):
    print(update.message.text)

    if update.message.text == "Новый плейлист":
        if len(playlists) >= MAX_PLAYLISTS:
            await update.message.reply_text("Вы достигли лимита по количеству плейлистов")
            return MAIN
        else:
            keyboard = [[telegram.KeyboardButton("Назад")]]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
            await update.message.reply_text("Назовите плейлист", reply_markup=reply_markup)
            return CREATE
    elif update.message.text in playlists:
        await update.message.reply_text(f"Плейлист {update.message.text}")
        context.user_data['cur_playlist_name'] = update.message.text
        await build_playlist_menu(update, context)
        return PLAYLIST
    else:
        await update.message.reply_text(f"Плейлист {update.message.text} не существует")


# Playlist menu
async def build_playlist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Удаление информации о текущий странице "удаления трека"
    context.user_data.pop("cur_page", None)

    keyboard = [
        [telegram.KeyboardButton("Список"), telegram.KeyboardButton("Добавить"), telegram.KeyboardButton("Удалить")],
        [telegram.KeyboardButton("Переименовать"), telegram.KeyboardButton("УДАЛИТЬ ПЛЕЙЛИСТ"),
         telegram.KeyboardButton("Назад")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Выберите действие с плейлистом {context.user_data['cur_playlist_name']}",
                                    reply_markup=reply_markup)
    return PLAYLIST


async def playlist_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text
    match action:
        case "Список":
            path = os.getcwd() + "/" + "Audio" + "/" + str(update.message.chat.id) + "/" + context.user_data[
                'cur_playlist_name'] + "/"
            for track in playlists[context.user_data['cur_playlist_name']]:
                print(track)
                await context.bot.send_audio(chat_id=update.message.chat.id, audio=path + track,
                                             title=playlists[context.user_data['cur_playlist_name']][track][1],
                                             performer=playlists[context.user_data['cur_playlist_name']][track][2],
                                             duration=playlists[context.user_data['cur_playlist_name']][track][3],
                                             write_timeout=9999999, read_timeout=99999999)

        case "Добавить":
            keyboard = [[telegram.KeyboardButton("Назад")]]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
            await update.message.reply_text("Отправьте треки, которые необходимо добавить", reply_markup=reply_markup)
            return ADD

        case "Удалить":
            # context.user_data["cur_playlist_page"] = 0
            print(playlists)
            print(playlists[context.user_data['cur_playlist_name']])
            keyboard = [
                [telegram.KeyboardButton(track) for track in
                 playlists[context.user_data['cur_playlist_name']]
                 # if 0 <= playlists[context.user_data['cur_playlist_name']][track][0] < 5],
                ],
                [  # telegram.KeyboardButton(u"\u25C0\uFE0F"),
                    telegram.KeyboardButton("Назад"),
                    # telegram.KeyboardButton(u"\u25B6\uFE0F")]
                ]
            ]

            reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите трек для удаления из плейлиста", reply_markup=reply_markup)
            return REMOVE

        case "Переименовать":
            keyboard = [[telegram.KeyboardButton("Назад")]]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
            await update.message.reply_text("Введите новое название плейлиста", reply_markup=reply_markup)
            return RENAME

        case "УДАЛИТЬ ПЛЕЙЛИСТ":
            keyboard = [[telegram.KeyboardButton("Назад")]]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Подтвердите удаление плейлиста {context.user_data['cur_playlist_name']}. Введите его полное название",
                reply_markup=reply_markup)
            return DELETE

        case "Назад":
            await build_start_menu(update, context)
            return MAIN


async def playlist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Путь к треку
    path = os.getcwd() + "/" + "Audio" + "/" + str(update.message.chat.id) + "/" + context.user_data[
        'cur_playlist_name'] + "/"

    full_title = update.message.audio.performer + " - " + update.message.audio.title

    # Проверка на наличие трека в плейлисте
    if full_title in playlists[context.user_data['cur_playlist_name']]:
        await update.message.reply_text(f"Трек {full_title} уже в плейлисте")
        return ADD

    # Скачивание отправленного аудио
    new_file = await update.message.audio.get_file()
    await new_file.download_to_drive(path + full_title)

    # Создание инфо файла
    playlists[context.user_data['cur_playlist_name']][full_title] = (
        len(playlists[context.user_data['cur_playlist_name']]),
        update.message.audio.title,
        update.message.audio.performer,
        update.message.audio.duration
    )

    with open("playlists.json", "w") as f:
        json.dump(playlists, f)

    print(full_title)
    print(update.message.audio)
    print(playlists[context.user_data['cur_playlist_name']][full_title])

    await update.message.reply_text(f"Трек {full_title} добавлен в плейлист")

    return ADD


async def playlist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = os.getcwd() + "/" + "Audio" + "/" + str(update.message.chat.id) + "/" + context.user_data[
        'cur_playlist_name'] + "/"

    if update.message.text in playlists[context.user_data['cur_playlist_name']]:
        os.remove(path + update.message.text)
        del playlists[context.user_data['cur_playlist_name']][update.message.text]

    # cur_page = context.user_data["cur_playlist_page"]

    keyboard = [
        [telegram.KeyboardButton(track) for track in
         playlists[context.user_data['cur_playlist_name']]
         # if cur_page * 5 <= playlists[context.user_data['cur_playlist_name']][track][0] < (cur_page + 1) * 5],
        ],
        [  # telegram.KeyboardButton(u"\u25C0\uFE0F"),
            telegram.KeyboardButton("Назад"),
            # telegram.KeyboardButton(u"\u25B6\uFE0F")]]
        ]
    ]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard)

    with open("playlists.json", "w") as f:
        json.dump(playlists, f)

    await update.message.reply_text(f"Трек {update.message.text} удален из плейлиста", reply_markup=reply_markup)
    return REMOVE


# async def rem_page_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     context.user_data["cur_playlist_page"] += 1
#     cur_page = context.user_data["cur_playlist_page"]
#
#     keyboard = [
#         [telegram.KeyboardButton(track) for track in
#          playlists[context.user_data['cur_playlist_name']] if cur_page * 5 <= playlists[context.user_data['cur_playlist_name']][track][0] < (cur_page + 1) * 5],
#         [telegram.KeyboardButton(u"\u25C0\uFE0F"),
#          telegram.KeyboardButton("Назад"),
#          telegram.KeyboardButton(u"\u25B6\uFE0F")]]
#     reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
#
#     await update.message.reply_text("", reply_markup=reply_markup)
#     return REMOVE
#
#
# async def rem_page_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     context.user_data["cur_playlist_page"] -= 1
#     cur_page = context.user_data["cur_playlist_page"]
#
#     keyboard = [
#         [telegram.KeyboardButton(track) for track in
#          playlists[context.user_data['cur_playlist_name']] if cur_page * 5 <= playlists[context.user_data['cur_playlist_name']][track][0] < (cur_page + 1) * 5],
#         [telegram.KeyboardButton(u"\u25C0\uFE0F"),
#          telegram.KeyboardButton("Назад"),
#          telegram.KeyboardButton(u"\u25B6\uFE0F")]]
#     reply_markup = telegram.ReplyKeyboardMarkup(keyboard)
#
#     await update.message.reply_text("", reply_markup=reply_markup)
#     return REMOVE


async def playlist_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    if new_name not in playlists:
        playlists[new_name] = playlists[context.user_data['cur_playlist_name']]
        del playlists[context.user_data['cur_playlist_name']]

        path = os.getcwd() + "/" + "Audio" + "/" + str(update.message.chat.id) + "/" + context.user_data[
            'cur_playlist_name']
        os.rename(path, os.getcwd() + "/" + "Audio" + "/" + str(update.message.chat.id) + "/" + update.message.text)

        context.user_data['cur_playlist_name'] = new_name

        await update.message.reply_text(f"Теперь плейлист называется {new_name}")

    else:
        await update.message.reply_text(f"Плейлист c именем {new_name} уже существует")

    await build_playlist_menu(update, context)
    return PLAYLIST


async def playlist_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == context.user_data['cur_playlist_name']:
        path = os.getcwd() + "\\" + "Audio" + "\\" + str(update.message.chat.id) + "\\" + context.user_data[
            'cur_playlist_name']
        rmtree(path)

        del playlists[context.user_data['cur_playlist_name']]
        with open("playlists.json", "w") as f:
            json.dump(playlists, f)

        await build_start_menu(update, context)
        return MAIN
    else:
        await build_playlist_menu(update, context)
        return PLAYLIST


# Playlist creating
async def new_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text

    if name not in playlists:
        playlists[name] = {}
        path = os.getcwd() + "/" + "Audio" + "/" + str(update.message.chat.id) + "/" + name + "/"
        os.makedirs(path)

        await update.message.reply_text(f"Плейлист {name} создан")

    else:
        await update.message.reply_text(f"Плейлист {name} уже существует")

    await build_start_menu(update, context)
    return MAIN


if __name__ == "__main__":
    application = Application.builder().token("6059715082:AAEBO0Gp05BigDY2IqyTAeXRkrvwKRzovMU").build()
    with open("playlists.json", "r") as f:
        playlists = json.load(f)
    main_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("Начать!"), build_start_menu),
                      CommandHandler("cancel", build_start_menu)],
        states={
            MAIN: [
                MessageHandler(filters.TEXT, start_menu_button)
            ],

            PLAYLIST: [
                MessageHandler(filters.Text(["Назад"]), build_start_menu),
                MessageHandler(filters.TEXT, playlist_button)
            ],

            ADD: [
                MessageHandler(filters.Text(["Назад"]), build_playlist_menu),
                MessageHandler(filters.AUDIO, playlist_add)
            ],

            REMOVE: [
                MessageHandler(filters.Text(["Назад"]), build_playlist_menu),
                MessageHandler(filters.TEXT, playlist_remove)
            ],

            RENAME: [
                MessageHandler(filters.Text(["Назад"]), build_playlist_menu),
                MessageHandler(filters.TEXT, playlist_rename)
            ],

            DELETE: [
                MessageHandler(filters.Text(["Назад"]), build_playlist_menu),
                MessageHandler(filters.TEXT, playlist_delete)
            ],

            CREATE: [
                MessageHandler(filters.Text(["Назад"]), build_start_menu),
                MessageHandler(filters.TEXT, new_playlist)
            ]
        },
        fallbacks=[]
    )
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(main_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)
