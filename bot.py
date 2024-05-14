import math
import telebot
import logging
import functools
from auto_token import update_config_file
from yandex_gpt import PyYandexGpt
from database_YaGPT import Tokens
from database_history import History
from database_SpeechKit import SpeechKit
from speechkit import text_to_speech, speech_to_text
from config import TOKEN, WHITELISTED_USERS
bot = telebot.TeleBot(TOKEN)
dbt = Tokens("tokens.db")
dbh = History("history.db")
dbS = SpeechKit()
gpt = PyYandexGpt()
logging.basicConfig(level=logging.DEBUG)
dbt.create_tables()
dbS.create_database()
system_prompt = "Ты - собеседник женского пола, общайся с пользователем"
def is_stt_block_limit(message, duration):
    chat_id = message.from_user.id
    audio_blocks = math.ceil(duration / 15)
    all_blocks = dbS.get_blocks_vount(chat_id)
    if duration >= 30:
        msg = "работает с голосовыми сообщениями меньше 30 секунд"
        bot.send_message(chat_id, msg)
        return None
    if all_blocks == 0:
        msg = "Исчерпаны все блоки, использование ограничено"
        bot.send_message(chat_id, msg)
        return None
    return audio_blocks
def is_user_whitelisted(chat_id):
    return chat_id in WHITELISTED_USERS
def whitelist_check(func):
    @functools.wraps(func)
    def wrapper(message):
        chat_id = message.chat.id
        if chat_id not in WHITELISTED_USERS:
            bot.send_message(chat_id, "У тебя нету доступа к этой команде/функционалу, так как ты не в вайтлисте (/whitelist)")
            return
        return func(message)
    return wrapper
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    dbh.create_table(chat_id)
    dbt.create_user_profile(chat_id)
    dbS.add_user(chat_id)
    bot.send_message(chat_id,
                     text=f"""
Привет, {user_name}! Я бот собесендник который может отвечать на голосовые и текстовые сообщения""")
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id,
                      text="""
Бот работает на базе YaGPT и SpeechKit
Чтобы проверить можете ли вы пользоватсья ботом: /whitelist""")
@bot.message_handler(commands=['update_token'])
def handle_update_token(message):
    update_config_file()
    bot.reply_to(message, "Токен обновлён")
@bot.message_handler(commands=['whitelist'])
def whitelist(message):
    chat_id = message.chat.id
    if is_user_whitelisted(chat_id):
        bot.send_message(chat_id, 'У вас есть доступ')
    else:
        bot.send_message(chat_id, 'У вас нету доступа')

@bot.message_handler(commands=['stt'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь голосовое сообщение')
    bot.register_next_step_handler(message, handle_stt)
@bot.message_handler(commands=['tts'])
@whitelist_check
def tts(message):
    chat_id = message.chat.id
    current_characters = dbS.get_token_count(chat_id)
    if current_characters == 0:
        bot.send_message(chat_id, "символов недостаточно")
        return
    bot.send_message(chat_id, "введите текст")
    bot.register_next_step_handler(message, handle_tts)
@bot.message_handler(commands=['debug'])
@whitelist_check
def debug(message):
    chat_id = message.chat.id
    try:
        with open('logs.log', 'rb') as log_file:
            bot.send_document(chat_id, log_file)
        bot.send_message(chat_id, "логи отправлены")
    except Exception as e:
        bot.send_message(chat_id, f"ошибка при отправке: {e}")
@bot.message_handler(commands=['clear'])
def clear(message):
    chat_id = message.chat.id
    dbh.clear_history(chat_id)
    bot.send_message(chat_id, "History cleared")
@bot.message_handler(commands=['profile'])
def tokens_handler(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    tokens = dbt.get_tokens(chat_id)
    symbols = dbS.get_token_count(chat_id)
    blocks = dbS.get_blocks_vount(chat_id)
    bot.send_message(chat_id, f"""Информация по пользователю {user_name}

Кол-во оставшихся токенов: {tokens}
Кол-ва оставшихся символов: {symbols}
Кол-во оставшихся блоков: {blocks}""")
@bot.message_handler(content_types=['text'])
@whitelist_check
def text_reply(message):
    chat_id = message.chat.id
    current_tokens = dbt.get_tokens(chat_id)
    if current_tokens == 0:
        bot.send_message(chat_id,
                         "Токены закончились, больше вы не можете пользоваться нейросетью")
    else:
        text = message.text
        user_history = dbh.get_history(message.chat.id)
        history_text = "\n".join([f"{row[0]}: {row[1]} ({row[2]})" for row in user_history])
        logging.info(f"История общения: {history_text}")
        final_text = f"{text}, История чата: {history_text}"
        system_text = system_prompt
        prompt = [{"role": "system",
                   "text": system_text},
                  {"role": "user",
                   "text": final_text}]
        response = gpt.create_request(chat_id, prompt)
        if response.status_code == 200:
            try:
                response_json = response.json()
                result_text = response_json['result']['alternatives'][0]['message']['text']
                logging.info(response_json)
                count = gpt.count_tokens(final_text)
                dbt.deduct_tokens(chat_id, count)
                bot.send_message(chat_id, result_text)
                dbh.save_message(chat_id, 'user', text)
                dbh.save_message(chat_id, 'assistant', result_text)
                logging.info(f"История ответа {chat_id} сохранена")
                return
            except KeyError:
                logging.error('Ответ не содержит "result"')
                bot.send_message(chat_id, "Не удалось сгенерировать историю.")
        else:
            logging.error(f'Ошибка API GPT: {response.status_code}')
            bot.send_message(chat_id, f"""
        ошибка при обращении к API GPT.
        Ошибка: {response.status_code}
        Если ошибка 429 - нейросеть слишком нагружена""")
            return
@bot.message_handler(content_types=['voice'])
@whitelist_check
def voice_reply(message):
    chat_id = message.chat.id
    if not message.voice:
        return
    stt_blocks = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        return
    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    status, text = speech_to_text(file)
    if status:
        dbS.update_blocks_count(chat_id,dbS.get_blocks_vount(chat_id) - stt_blocks)
        current_tokens = dbt.get_tokens(chat_id)
        if current_tokens == 0:
            bot.send_message(chat_id,
                             "токены закончились")
        else:
            text = status
            user_history = dbh.get_history(message.chat.id)
            history_text = "\n".join([f"{row[0]}: {row[1]} ({row[2]})" for row in user_history])
            logging.info(f"История общения: {history_text}")
            final_text = f"{text}, История чата: {history_text}"
            system_text = system_prompt
            prompt = [{"role": "system",
                       "text": system_text},
                      {"role": "user",
                       "text": final_text}]
            response = gpt.create_request(chat_id, prompt)
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    result_text = response_json['result']['alternatives'][0]['message']['text']
                    logging.info(response_json)
                    count = gpt.count_tokens(final_text)
                    dbt.deduct_tokens(chat_id, count)
                    dbh.save_message(chat_id, 'user', text)
                    dbh.save_message(chat_id, 'assistant', result_text)
                    logging.info(f"История ответа от пользователя {chat_id} сохранена")
                    current_characters = dbS.get_token_count(chat_id)
                    text = result_text
                    if current_characters - len(text) < 0:
                        bot.send_message(chat_id, "лимит токенов превышен")
                        return
                    current_characters = dbS.get_token_count(chat_id)
                    success, audio_file_path = text_to_speech(text, str(chat_id))
                    if success:
                        dbS.update_token_count(chat_id, current_characters - len(text))
                        bot.send_audio(chat_id, open(audio_file_path, 'rb'))
                    else:
                        bot.send_message(chat_id, "ошибка")
                except KeyError:
                    logging.error('Ответ не содержит "result"')
                    bot.send_message(chat_id, "не удалось сгенерировать историю.")
            else:
                logging.error(f'Ошибка API GPT: {response.status_code}')
                bot.send_message(chat_id, f"""
                ошибка при обращении к API GPT.
                Ошибка: {response.status_code}
                Если ошибка 429 - нейросеть слишком нагружена""")
                return
def handle_tts(message):
    chat_id = message.chat.id
    text = message.text
    current_characters = dbS.get_token_count(chat_id)
    if current_characters - len(text) < 0:
        bot.send_message(chat_id, "Лимит токенов превышен")
        return
    current_characters = dbS.get_token_count(chat_id)
    success, audio_file_path = text_to_speech(text, str(chat_id))
    if success:
        dbS.update_token_count(chat_id, current_characters - len(text))
        bot.send_audio(chat_id, open(audio_file_path, 'rb'))
    else:
        bot.send_message(chat_id, "Error")
def handle_stt(message):
    chat_id = message.from_user.id
    if not message.voice:
        return
    stt_blocks = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        return

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    status, text = speech_to_text(file)
    if status:
        bot.send_message(chat_id, text, reply_to_message_id=message.id)
        dbS.update_blocks_count(chat_id,dbS.get_blocks_vount(chat_id) - stt_blocks)
    else:
        bot.send_message(chat_id, text)
if __name__ == "__main__":
    print("Бот запускается...")
    logging.info("Бот запускается...")
    bot.polling()