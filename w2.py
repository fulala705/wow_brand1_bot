import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- ቅንብሮች (Settings) ---
API_TOKEN = '8279546444:AAGwB_hc6gjvPe3_pBlSPdl7eRFFjV8d9nw'
ADMIN_ID = 1623014823  # የራስሽን_ID_እዚህ_አስገቢ (ለምሳሌ፡ 56789012)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "shoe_store.db")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- ዳታቤዝ ማዘጋጀት ---
def init_db():
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    # አዳዲስ ኮለሞች (description እና phone) እዚህ ተካተዋል
    cursor.execute('''CREATE TABLE IF NOT EXISTS shoes 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       name TEXT, 
                       price REAL, 
                       stock INTEGER, 
                       size TEXT, 
                       description TEXT, 
                       phone TEXT, 
                       photo_id TEXT)''')
    
    # የድሮ ዳታቤዝ ካለሽ እነዚህን ኮለሞች በግድ እንዲጨምር ለማድረግ (Migration)
    try:
        cursor.execute("ALTER TABLE shoes ADD COLUMN description TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE shoes ADD COLUMN phone TEXT")
    except sqlite3.OperationalError: pass
        
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- የመመዝገቢያ ሁኔታዎች (States) ---
class AddProduct(StatesGroup):
    name = State()
    price = State()
    size = State()
    description = State()
    phone = State()
    stock = State()
    photo = State()

# --- ቁልፎች (Keyboards) ---
def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("አዲስ ጫማ መመዝገብ", "ያሉ ጫማዎች")
    return kb

def user_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("ያሉ ጫማዎች")
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("እንኳን መጡ ባለቤት! ምን መስራት ይፈልጋሉ?", reply_markup=admin_kb())
    else:
        await message.answer("እንኳን ወደ ጫማ ቤታችን መጡ! የሚፈልጉትን ጫማ ስም በመጻፍ መፈለግ ይችላሉ።", reply_markup=user_kb())

# --- የባለቤት ክፍል (ምዝገባ) ---
@dp.message_handler(text="አዲስ ጫማ መመዝገብ")
async def add_shoe(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await AddProduct.name.set()
    await message.answer("የጫማውን ስም ያስገቡ:")

@dp.message_handler(state=AddProduct.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await AddProduct.next()
    await message.answer("ዋጋውን ያስገቡ (በብር):")

@dp.message_handler(state=AddProduct.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await AddProduct.next()
    await message.answer("መጠን (Size) ያስገቡ (ለምሳሌ: 40-44):")

@dp.message_handler(state=AddProduct.size)
async def process_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await AddProduct.next()
    await message.answer("ስለ ጫማው አጭር መግለጫ (Description) ያስገቡ:")

@dp.message_handler(state=AddProduct.description)
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await AddProduct.next()
    await message.answer("የመሸጫ ስልክ ቁጥር ያስገቡ:")

@dp.message_handler(state=AddProduct.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await AddProduct.next()
    await message.answer("ያለውን ብዛት (Stock) ያስገቡ:")

@dp.message_handler(state=AddProduct.stock)
async def process_stock(message: types.Message, state: FSMContext):
    await state.update_data(stock=message.text)
    await AddProduct.next()
    await message.answer("አሁን ደግሞ የጫማውን ፎቶ ላኩልኝ:")

@dp.message_handler(content_types=['photo'], state=AddProduct.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    
    cursor.execute('''INSERT INTO shoes (name, price, stock, size, description, phone, photo_id) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (data['name'], data['price'], data['stock'], data['size'], 
                    data['description'], data['phone'], photo_id))
    conn.commit()
    await message.answer(f"✅ {data['name']} በተሳካ ሁኔታ ተመዝግቧል!", reply_markup=admin_kb())
    await state.finish()

# --- የመልዕክት አጻጻፍ (Caption Formatting) ---
def format_caption(item):
    # ID: 0, Name: 1, Price: 2, Stock: 3, Size: 4, Desc: 5, Phone: 6, Photo: 7
    return (f"👟 ስም: {item[1]}\n"
            f"💰 ዋጋ: {item[2]} ብር\n"
            f"📏 መጠን (Size): {item[4]}\n"
            f"📝 መግለጫ: {item[5]}\n"
            f"📞 ስልክ: {item[6]}\n"
            f"📦 ክምችት: {item[3]}")

# --- ጫማዎችን የማሳያ ተግባር ---
@dp.message_handler(text="ያሉ ጫማዎች")
async def show_shoes(message: types.Message):
    cursor.execute("SELECT * FROM shoes")
    items = cursor.fetchall()
    if not items:
        await message.answer("ምንም የተመዘገበ ጫማ የለም።")
        return
    for item in items:
        await bot.send_photo(message.chat.id, item[7], caption=format_caption(item))

# --- የፍለጋ ተግባር ---
@dp.message_handler()
async def search_shoes(message: types.Message):
    # 'ያሉ ጫማዎች' የሚለውን ጽሁፍ ሌላኛው handler እንዲይዘው ይዘለላል
    if message.text == "ያሉ ጫማዎች": return
    
    cursor.execute("SELECT * FROM shoes WHERE name LIKE ?", (f'%{message.text}%',))
    results = cursor.fetchall()
    if not results:
        await message.answer("ይቅርታ፣ በዚሁ ስም የተመዘገበ ጫማ አልተገኘም።")
        return
    for row in results:
        await bot.send_photo(message.chat.id, row[7], caption=format_caption(row))

# --- ቦቱን ማስነሳት ---
if __name__ == '__main__':
    print("ቦቱ ስራ ጀምሯል...")
    executor.start_polling(dp, skip_updates=True)