import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- ቅንብሮች (Settings) ---
API_TOKEN = '8279546444:AAGUR4WA44Aw-LCi-2aov0j98xBB9KTdrcc'
ADMIN_ID = 1623014823 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "shoe_store.db")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- 1. ዳታቤዝ ማዘጋጀት ---
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

# --- 2. የሁኔታዎች መቆጣጠሪያ (FSM States) ---
class AddProduct(StatesGroup):
    name = State()
    price = State()
    size = State()
    description = State()
    phone = State()
    stock = State()
    photo = State()

class CustomerOrder(StatesGroup):
    waiting_for_size = State()
    waiting_for_phone = State()
    waiting_for_name = State()

# --- 3. ቁልፎች (Keyboards) ---
def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("➕ አዲስ ጫማ መመዝገብ", "👟 ያሉ ጫማዎች")
    return kb

def user_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👟 ጫማዎችን እይ", "📞 ስለ እኛ")
    return kb

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ አቋርጥ")
    return kb

def buy_button(shoe_id, shoe_name):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text=f"🛍️ {shoe_name}ን እዘዝ", callback_data=f"buy_{shoe_id}"))
    return kb

# --- 4. Start & Cancel Handlers (ቅድሚያ የሚሰጣቸው) ---
@dp.message_handler(commands=['start'], state="*")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish() # ማንኛውንም የተጀመረ ሂደት ያጸዳል
    if message.from_user.id == ADMIN_ID:
        await message.answer("እንኳን መጡ ባለቤት! ምን መስራት ይፈልጋሉ?", reply_markup=admin_kb())
    else:
        await message.answer("እንኳን ወደ <b>WOW Brand Shoes</b> በደህና መጡ! 👟", reply_markup=user_kb())

@dp.message_handler(text="❌ አቋርጥ", state="*")
async def cancel_action(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.answer("ሂደቱ ተቋርጧል!", reply_markup=admin_kb() if message.from_user.id == ADMIN_ID else user_kb())

# --- 5. የምዝገባ ሂደት (Admin Only) ---
@dp.message_handler(text="➕ አዲስ ጫማ መመዝገብ", user_id=ADMIN_ID)
async def add_shoe_start(message: types.Message):
    await AddProduct.name.set()
    await message.answer("<b>የጫማውን ስም ያስገቡ:</b>", reply_markup=cancel_kb())

@dp.message_handler(state=AddProduct.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await AddProduct.price.set()
    await message.answer("<b>ዋጋውን ያስገቡ (በብር):</b>")

@dp.message_handler(state=AddProduct.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await AddProduct.size.set()
    await message.answer("<b>ሳይዝ (Size) ያስገቡ (ምሳሌ: 40-44):</b>")

@dp.message_handler(state=AddProduct.size)
async def process_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await AddProduct.description.set()
    await message.answer("<b>ስለ ጫማው አጭር መግለጫ (Description):</b>")

@dp.message_handler(state=AddProduct.description)
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await AddProduct.phone.set()
    await message.answer("<b>የመሸጫ ስልክ ቁጥር ያስገቡ:</b>")

@dp.message_handler(state=AddProduct.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await AddProduct.stock.set()
    await message.answer("<b>ያለውን ብዛት (Stock) ያስገቡ:</b>")

@dp.message_handler(state=AddProduct.stock)
async def process_stock(message: types.Message, state: FSMContext):
    await state.update_data(stock=message.text)
    await AddProduct.photo.set()
    await message.answer("<b>አሁን የጫማውን ፎቶ ላኩልኝ:</b>")

@dp.message_handler(content_types=['photo'], state=AddProduct.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    cursor.execute('''INSERT INTO shoes (name, price, stock, size, description, phone, photo_id) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (data['name'], data['price'], data['stock'], data['size'], 
                    data['description'], data['phone'], photo_id))
    conn.commit()
    await state.finish()
    await message.answer("<b>✅ ጫማው በትክክል ተመዝግቧል!</b>", reply_markup=admin_kb())

# --- 6. የግዢ ሂደት (Order Flow) ---
@dp.callback_query_handler(lambda c: c.data.startswith('buy_'), state="*")
async def start_order(callback_query: types.CallbackQuery, state: FSMContext):
    shoe_id = callback_query.data.split('_')[1]
    cursor.execute("SELECT name, price FROM shoes WHERE id=?", (shoe_id,))
    shoe = cursor.fetchone()
    await state.update_data(order_shoe_name=shoe[0], order_shoe_price=shoe[1], order_shoe_id=shoe_id)
    await CustomerOrder.waiting_for_size.set()
    await bot.send_message(callback_query.from_user.id, f"<b>ለ {shoe[0]} የሚፈልጉትን ሳይዝ (Size) ይጻፉ:</b>", reply_markup=cancel_kb())

@dp.message_handler(state=CustomerOrder.waiting_for_size)
async def order_size(message: types.Message, state: FSMContext):
    await state.update_data(customer_size=message.text)
    await CustomerOrder.waiting_for_phone.set()
    await message.answer("<b>ስልክ ቁጥርዎን ያስገቡ:</b>")

@dp.message_handler(state=CustomerOrder.waiting_for_phone)
async def order_phone(message: types.Message, state: FSMContext):
    await state.update_data(customer_phone=message.text)
    await CustomerOrder.waiting_for_name.set()
    await message.answer("<b>ሙሉ ስምዎን ያስገቡ:</b>")

@dp.message_handler(state=CustomerOrder.waiting_for_name)
async def order_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("<b>✅ ትዕዛዝዎ ተልኳል! እናመሰግናለን።</b>", reply_markup=user_kb())
    admin_msg = (f"🚨 <b>አዲስ ትዕዛዝ!</b>\n\n👟 {data['order_shoe_name']}\n📏 ሳይዝ: {data['customer_size']}\n"
                 f"👤 ደንበኛ: {message.text}\n📞 ስልክ: {data['customer_phone']}")
    cursor.execute("SELECT photo_id FROM shoes WHERE id=?", (data['order_shoe_id'],))
    photo = cursor.fetchone()
    await bot.send_photo(ADMIN_ID, photo[0], caption=admin_msg)
    await state.finish()

# --- 7. ጫማዎችን የማሳያ ተግባር (Global) ---
def format_caption(item):
    return (f"👟 <b>ስም: {item[1]}</b>\n💰 ዋጋ: {item[2]} ብር\n📏 ሳይዝ: {item[4]}\n"
            f"📝 መግለጫ: {item[5]}\n📦 ሁኔታ: {'✅ አለ' if int(item[3]) > 0 else '❌ አልቋል'}")

@dp.message_handler(text=["👟 ጫማዎችን እይ", "👟 ያሉ ጫማዎች"], state="*")
async def show_shoes(message: types.Message, state: FSMContext):
    await state.finish()
    cursor.execute("SELECT * FROM shoes")
    items = cursor.fetchall()
    if not items:
        await message.answer("<b>አሁን ላይ ምንም ጫማ የለም።</b>")
        return
    for item in items:
        await bot.send_photo(message.chat.id, item[7], caption=format_caption(item), 
                             reply_markup=buy_button(item[0], item[1]))

# --- 8. የፍለጋ ተግባር (ሁልጊዜ በመጨረሻ መሆን አለበት!) ---
@dp.message_handler(state=None) # state=None ማለት ምንም ምዝገባ ውስጥ ካልሆንክ ብቻ ይሰራል።
async def search_shoes(message: types.Message):
    # አዝራሮችን እንዲዘል ለማድረግ
    if message.text in ["📞 ስለ እኛ"]: return
    
    cursor.execute("SELECT * FROM shoes WHERE name LIKE ?", (f'%{message.text}%',))
    results = cursor.fetchall()
    if not results:
        await message.answer("<b>ይቅርታ፣ አልተገኘም። እባክዎ በትክክል ይጻፉ።</b>")
        return
    for row in results:
        await bot.send_photo(message.chat.id, row[7], caption=format_caption(row), 
                             reply_markup=buy_button(row[0], row[1]))

if __name__ == '__main__':
    print("ዘመናዊው ቦት ስራ ጀምሯል...")
    executor.start_polling(dp, skip_updates=True)
