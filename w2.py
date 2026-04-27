import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- ቅንብሮች ---
API_TOKEN = '8279546444:AAGUR4WA44Aw-LCi-2aov0j98xBB9KTdrcc'
ADMIN_ID = 1623014823 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "shoe_store.db")

# --- ዳታቤዝ ---
def init_db():
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS shoes 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       name TEXT, price REAL, stock INTEGER, 
                       size TEXT, description TEXT, phone TEXT, photo_id TEXT)''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- ሁኔታዎች (States) ---
class AddProduct(StatesGroup):
    name = State()
    price = State()
    size = State()
    description = State()
    phone = State()
    stock = State()
    photo = State()

# --- ቁልፎች ---
def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id == ADMIN_ID:
        kb.add("➕ አዲስ ጫማ", "📋 ያሉ ጫማዎች", "💾 Database Backup")
    else:
        kb.add("📋 ያሉ ጫማዎች", "🔍 ፈልግ")
    return kb

def cancel_kb():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ አቋርጥ")

def order_button(shoe_id, shoe_name):
    btn = InlineKeyboardMarkup()
    btn.add(InlineKeyboardButton(text=f"🛍️ {shoe_name}ን እዘዝ", callback_data=f"order_{shoe_id}"))
    return btn

# --- 1. Start & Cancel ---
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("እንኳን ወደ <b>Wow Brand</b> ጫማ መደብር በሰላም መጡ! 👟", reply_markup=main_menu(message.from_user.id))

@dp.message_handler(text="❌ አቋርጥ", state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("ሂደቱ ተቋርጧል።", reply_markup=main_menu(message.from_user.id))

# --- 2. የባለቤት ክፍል (Database Backup) ---
@dp.message_handler(text="💾 Database Backup", user_id=ADMIN_ID, state="*")
async def send_db(message: types.Message):
    if os.path.exists(db_path):
        with open(db_path, 'rb') as db_file:
            await bot.send_document(ADMIN_ID, db_file, caption="የዛሬው የዳታቤዝ መረጃ (Backup)")
    else:
        await message.answer("ዳታቤዙ ገና አልተፈጠረም።")

# --- 3. አዲስ ጫማ መመዝገቢያ (AddProduct flow) ---
@dp.message_handler(text="➕ አዲስ ጫማ", user_id=ADMIN_ID)
async def add_shoe(message: types.Message):
    await AddProduct.name.set()
    await message.answer("የጫማውን ስም ያስገቡ:", reply_markup=cancel_kb())

@dp.message_handler(state=AddProduct.name)
async def proc_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await AddProduct.next()
    await m.answer("ዋጋውን ያስገቡ:")

@dp.message_handler(state=AddProduct.price)
async def proc_price(m: types.Message, state: FSMContext):
    await state.update_data(price=m.text)
    await AddProduct.next()
    await m.answer("መጠን (Size) ያስገቡ (ምሳሌ: 40-44):")

@dp.message_handler(state=AddProduct.size)
async def proc_size(m: types.Message, state: FSMContext):
    await state.update_data(size=m.text)
    await AddProduct.next()
    await m.answer("ስለ ጫማው አጭር መግለጫ ያስገቡ:")

@dp.message_handler(state=AddProduct.description)
async def proc_desc(m: types.Message, state: FSMContext):
    await state.update_data(description=m.text)
    await AddProduct.next()
    await m.answer("የእርሶን ስልክ ቁጥር ያስገቡ:")

@dp.message_handler(state=AddProduct.phone)
async def proc_phone(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text)
    await AddProduct.next()
    await m.answer("ያለውን ብዛት (Stock) ያስገቡ:")

@dp.message_handler(state=AddProduct.stock)
async def proc_stock(m: types.Message, state: FSMContext):
    await state.update_data(stock=m.text)
    await AddProduct.next()
    await m.answer("አሁን የጫማውን ፎቶ ላኩልኝ:")

@dp.message_handler(content_types=['photo'], state=AddProduct.photo)
async def proc_photo(m: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = m.photo[-1].file_id
    cursor.execute('''INSERT INTO shoes (name, price, stock, size, description, phone, photo_id) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (data.get('name'), data.get('price'), data.get('stock'), data.get('size'), 
                    data.get('description'), data.get('phone'), photo_id))
    conn.commit()
    await state.finish()
    await m.answer("✅ ጫማው ተመዝግቧል!", reply_markup=main_menu(ADMIN_ID))
    
    # አውቶማቲክ ባካፕ
    with open(db_path, 'rb') as db_file:
        await bot.send_document(ADMIN_ID, db_file, caption=f"አዲስ ጫማ ተመዝግቧል: {data.get('name')}")

# --- 4. የትዕዛዝ ሂደት (Order Flow) ---
@dp.callback_query_handler(lambda c: c.data.startswith('order_'))
async def process_order(callback_query: types.CallbackQuery):
    shoe_id = callback_query.data.split('_')[1]
    cursor.execute("SELECT name FROM shoes WHERE id=?", (shoe_id,))
    shoe = cursor.fetchone()
    user = callback_query.from_user
    
    # ለባለቤቱ ማሳወቂያ መላክ
    order_text = (f"🔔 <b>አዲስ ትዕዛዝ!</b>\n\n"
                  f"👤 ደንበኛ: {user.full_name}\n"
                  f"🆔 ID: <code>{user.id}</code>\n"
                  f"👟 ጫማ: {shoe[0] if shoe else 'ያልታወቀ'}")
    
    await bot.send_message(ADMIN_ID, order_text)
    await bot.answer_callback_query(callback_query.id, "ትዕዛዝዎ ለባለቤቱ ደርሷል! በቅርቡ ያነጋግሩዎታል።", show_alert=True)

# --- 5. ጫማዎችን ማሳያ ---
def format_caption(item):
    return (f"👟 <b>ስም: {item[1]}</b>\n"
            f"💰 <b>ዋጋ: {item[2]} ብር</b>\n"
            f"📏 <b>Size: {item[4]}</b>\n"
            f"📝 <b>መግለጫ:</b> {item[5]}\n"
            f"📞 <b>ስልክ:</b> {item[6]}")

@dp.message_handler(text="📋 ያሉ ጫማዎች", state="*")
async def show_shoes(message: types.Message, state: FSMContext):
    await state.finish()
    cursor.execute("SELECT * FROM shoes")
    items = cursor.fetchall()
    if not items:
        await message.answer("ምንም የተመዘገበ ጫማ የለም።")
        return
    for item in items:
        await bot.send_photo(message.chat.id, item[7], caption=format_caption(item), reply_markup=order_button(item[0], item[1]))

# --- 6. የፍለጋ ተግባር (በጣም መጨረሻ ላይ መሆን አለበት) ---
@dp.message_handler(state=None)
async def search_or_find(message: types.Message):
    if message.text in ["🔍 ፈልግ", "🔍"]:
        await message.answer("ለመፈለግ የጫማውን ስም ይጻፉልኝ:")
        return

    cursor.execute("SELECT * FROM shoes WHERE name LIKE ?", (f'%{message.text}%',))
    results = cursor.fetchall()
    if not results:
        await message.answer("ይቅርታ፣ አልተገኘም። እባክዎ በትክክል ይጻፉ።")
        return
    for row in results:
        await bot.send_photo(message.chat.id, row[7], caption=format_caption(row), reply_markup=order_button(row[0], row[1]))

# --- ቦቱን ማስነሳት ---
if __name__ == '__main__':
    print("ቦቱ ስራ ጀምሯል...")
    executor.start_polling(dp, skip_updates=True)
