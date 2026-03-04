import os
import re
import telebot
from telebot import types
from collections import defaultdict
from PIL import Image
from fpdf import FPDF
import pillow_heif
from dotenv import load_dotenv

# === System Configuration ===
load_dotenv()
# Securely fetching the token from environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
TEMP_DIR = 'temp_downloads'

# Registering HEIF opener for native Apple image support
pillow_heif.register_heif_opener()
bot = telebot.TeleBot(TOKEN)

# === Session & State Management ===
user_files = defaultdict(list)
# Default settings: Portrait orientation, High quality (95)
user_settings = defaultdict(lambda: {
    'orientation': 'P',
    'quality': 95        
})
user_states = {}

# --- Utility Functions ---

def cleanup_user_data(user_id):
    """Clears temporary files and resets user session state."""
    if user_id in user_files:
        for file_path in user_files[user_id]:
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"[ERROR] Failed to delete {file_path}: {e}")
        del user_files[user_id]
    
    user_states.pop(user_id, None)

def sanitize_filename(filename):
    """Removes invalid characters from the provided filename."""
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    return re.sub(r'[\\/*?:"<>|]', "", filename)

# --- Settings & UI Handlers ---

def get_settings_markup(user_id):
    """Generates an inline keyboard for PDF parameter tuning."""
    settings = user_settings[user_id]
    
    orientation_label = "Portrait" if settings['orientation'] == 'P' else "Landscape"
    quality_label = "High" if settings['quality'] == 95 else "Compressed"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"Orientation: {orientation_label}", callback_data="toggle_orientation"))
    markup.add(types.InlineKeyboardButton(f"Quality: {quality_label}", callback_data="toggle_quality"))
    markup.add(types.InlineKeyboardButton("✅ Save Settings", callback_data="close_settings"))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if call.data == 'toggle_orientation':
        user_settings[user_id]['orientation'] = 'L' if user_settings[user_id]['orientation'] == 'P' else 'P'
    elif call.data == 'toggle_quality':
        user_settings[user_id]['quality'] = 75 if user_settings[user_id]['quality'] == 95 else 95
    elif call.data == 'close_settings':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Settings saved!")
        return

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(user_id))
    bot.answer_callback_query(call.id)

# --- Core Logic Handlers ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    cleanup_user_data(user_id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📄 Build PDF", "🗑 Clear All", "⚙️ Settings")
    
    bot.send_message(
        user_id,
        "👋 **Universal Image-to-PDF Converter**\n\n"
        "1. Send images (JPG, PNG, HEIC).\n"
        "2. Configure parameters via 'Settings'.\n"
        "3. Press 'Build PDF' to generate your document.",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_states.get(m.from_user.id) != 'awaiting_filename')
def handle_incoming_images(message):
    user_id = message.from_user.id
    is_photo = message.content_type == 'photo'
    is_valid_doc = message.document and message.document.file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.heic'))
    
    if not (is_photo or is_valid_doc):
        bot.reply_to(message, "❗ Supported formats: JPG, PNG, HEIC.")
        return

    try:
        bot.send_chat_action(user_id, 'upload_photo')
        file_id = message.photo[-1].file_id if is_photo else message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        
        file_path = os.path.join(TEMP_DIR, f"{user_id}_{len(user_files[user_id])}_{file_info.file_path.split('/')[-1]}")
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        user_files[user_id].append(file_path)
        bot.reply_to(message, f"✅ Image **#{len(user_files[user_id])}** added.")
    except Exception as e:
        print(f"[ERROR] Processing failure: {e}")
        bot.reply_to(message, "😕 Processing error. Please try again.")

@bot.message_handler(func=lambda message: message.text in ["📄 Build PDF", "⚙️ Settings", "🗑 Clear All"])
def handle_menu(message):
    if message.text == "📄 Build PDF":
        user_id = message.from_user.id
        if not user_files[user_id]:
            bot.send_message(user_id, "❗ Please upload images first.")
            return
        user_states[user_id] = 'awaiting_filename'
        bot.send_message(user_id, "✏️ **Enter PDF filename:**", parse_mode='Markdown', reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "⚙️ Settings":
        bot.send_message(message.from_user.id, "⚙️ **PDF Configuration**", reply_markup=get_settings_markup(message.from_user.id), parse_mode='Markdown')
    elif message.text == "🗑 Clear All":
        cleanup_user_data(message.from_user.id)
        bot.send_message(message.from_user.id, "🗑 Session cleared.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_filename')
def finalize_pdf(message):
    user_id = message.from_user.id
    filename = sanitize_filename(message.text)
    del user_states[user_id]
    
    bot.send_message(user_id, f"⏳ **Generating `{filename}`...**", parse_mode='Markdown')
    bot.send_chat_action(user_id, 'upload_document')

    try:
        settings = user_settings[user_id]
        pdf = FPDF(orientation=settings['orientation'])
        
        for image_path in user_files[user_id]:
            image = Image.open(image_path).convert("RGB")
            temp_jpg = image_path + '.jpg'
            image.save(temp_jpg, 'jpeg', quality=settings['quality'])
            
            pdf.add_page()
            w, h = (190, 277) if settings['orientation'] == 'P' else (277, 190)
            pdf.image(temp_jpg, x=10, y=10, w=w)
            os.remove(temp_jpg)

        output_path = os.path.join(TEMP_DIR, filename)
        pdf.output(output_path)

        with open(output_path, 'rb') as f:
            bot.send_document(user_id, f, caption=f"✅ Your PDF `{filename}` is ready!")
        os.remove(output_path)
    except Exception as e:
        print(f"[CRITICAL] PDF Engine failure: {e}")
        bot.send_message(user_id, "❌ Critical error during synthesis.")
    finally:
        cleanup_user_data(user_id)

if __name__ == '__main__':
    print("[SYSTEM] Image-to-PDF Bot is operational.")
    bot.infinity_polling()
