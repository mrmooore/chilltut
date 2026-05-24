import logging
import random
import html  # Заменили кастомный экранизатор на надежный стандартный HTML-escape
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ═══════════════════════════════════════════
# НАСТРОЙКИ
# ═══════════════════════════════════════════
TOKEN = "8862192483:AAGI2bwDL7pjNJFFAMpL461m437ChNqCopM"
ADMIN_USERNAME = "@Chill_TooT_Vrn"

# TODO: Укажите здесь ваш цифровой ID из @userinfobot (например: 512345678)
ADMIN_CHAT_ID = 0  

PREPAYMENT_PERCENT = 20

PRICES = {
    "PS5 Slim": 1149,
    "PS4 Slim": 799,
    "PS VR2": 999,
    "Руль Logitech G29": 999,
    "Доп. джойстик PS5": 699,
    "Доп. джойстик PS4": 399,
    "Кальян": 849,
    "Уголь (10шт)": 399,
    "Табак (25-30г)": 250,
    "Плитка": 349,
    "Личный кальянщик": 1149,
    "Чай (уточнить)": 0,
}

# ═══════════════════════════════════════════
# СОСТОЯНИЯ РАЗГОВОРА
# ═══════════════════════════════════════════
(
    START, HOW_ARE_YOU, GET_ADDRESS, GET_SOURCE, 
    CATEGORY_CHOICE, PS_CHOICE, PS_DAYS, 
    HOOKAH_CHOICE, HOOKAH_DAYS,
    TEA_CHOICE, FOOD_CHOICE,
    CONFIRM_ORDER
) = range(12)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

orders_db = {}
order_counter = [1000]

def get_order_id():
    order_counter[0] += 1
    return order_counter[0]

# ═══════════════════════════════════════════
# КЛАВИАТУРЫ
# ═══════════════════════════════════════════

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")],
        [InlineKeyboardButton("📋 Мои заказы", callback_data="history"),
         InlineKeyboardButton("🎲 Бросить кубик", callback_data="dice")],
    ])

def category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 PlayStation", callback_data="cat_ps")],
        [InlineKeyboardButton("💨 Кальян", callback_data="cat_hookah")],
        [InlineKeyboardButton("🍵 Чай", callback_data="cat_tea")],
        [InlineKeyboardButton("🍔 Еда и напитки", callback_data="cat_food")],
        [InlineKeyboardButton("✅ Готово — оформить заказ", callback_data="cat_done")],
    ])

def ps_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("PS5 Slim — 1149₽/сут", callback_data="ps_PS5 Slim")],
        [InlineKeyboardButton("PS4 Slim — 799₽/сут", callback_data="ps_PS4 Slim")],
        [InlineKeyboardButton("PS VR2 — от 999₽/сут", callback_data="ps_PS VR2")],
        [InlineKeyboardButton("Руль Logitech G29 — 999₽/сут", callback_data="ps_Руль Logitech G29")],
        [InlineKeyboardButton("Доп. джойстик PS5 — 699₽", callback_data="ps_Доп. джойстик PS5")],
        [InlineKeyboardButton("Доп. джойстик PS4 — 399₽", callback_data="ps_Доп. джойстик PS4")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_category")],
    ])

def hookah_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💨 Кальян — 849₽/сут", callback_data="hook_Кальян")],
        [InlineKeyboardButton("🪨 Уголь (10шт) — 399₽", callback_data="hook_Уголь (10шт)")],
        [InlineKeyboardButton("🌿 Табак (25-30г) — от 250₽", callback_data="hook_Табак (25-30г)")],
        [InlineKeyboardButton("🔥 Плитка — 349₽", callback_data="hook_Плитка")],
        [InlineKeyboardButton("👨‍🍳 Личный кальянщик — 1149₽/час", callback_data="hook_Личный кальянщик")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_category")],
    ])

def days_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 день", callback_data="days_1"),
         InlineKeyboardButton("2 дня", callback_data="days_2"),
         InlineKeyboardButton("3 дня", callback_data="days_3")],
        [InlineKeyboardButton("Написать вручную", callback_data="days_manual")],
    ])

def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Изменить", callback_data="confirm_edit")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_cancel")],
    ])

def source_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Мею с кальянами", callback_data="src_hookah_menu")],
        [InlineKeyboardButton("📄 Меню без кальянов", callback_data="src_no_hookah_menu")],
        [InlineKeyboardButton("🔗 Другой источник", callback_data="src_other")],
    ])

# ═══════════════════════════════════════════
# СТАРТ И ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    global ADMIN_CHAT_ID
    
    if f"@{user.username}" == ADMIN_USERNAME:
        ADMIN_CHAT_ID = update.effective_chat.id
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}! Твой актуальный chat_id подтвержден: <b>{ADMIN_CHAT_ID}</b>.\nВсе заказы поступают сюда.",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data['cart'] = []
    context.user_data['user_id'] = user.id
    context.user_data['username'] = f"@{user.username}" if user.username else user.first_name

    await update.message.reply_text(
        "Привет! Что хочешь сделать? 👇",
        reply_markup=main_menu_keyboard()
    )
    return START

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Что хочешь сделать? 👇",
        reply_markup=main_menu_keyboard()
    )
    return START

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "order":
        await query.edit_message_text(
            f"👋 Привет! Добро пожаловать в <b>Chill TooT</b> 🎮💨\n\n"
            f"Мы доставим всё для твоего отдыха прямо к тебе.\n\n"
            f"Кстати, как ты сегодня? 😊",
            parse_mode="HTML"
        )
        return HOW_ARE_YOU
    
    elif query.data == "history":
        return await show_history(update, context)
    
    elif query.data == "dice":
        return await roll_dice(update, context)

async def how_are_you(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Отлично, приятно слышать! 😊\n\n"
        f"Напиши свой <b>адрес</b> — куда доставить? 📍\n"
        f"<i>(улица, дом, квартира или название объекта)</i>",
        parse_mode="HTML"
    )
    return GET_ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text(
        "Откуда ты узнал о нас? 👇",
        reply_markup=source_keyboard()
    )
    return GET_SOURCE

async def get_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    src_map = {
        "src_hookah_menu": "Меню с кальянами ✅",
        "src_no_hookah_menu": "Меню без кальянов",
        "src_other": "Другой источник"
    }
    
    source = src_map.get(query.data, "Не указан")
    context.user_data['source'] = source
    context.user_data['has_hookah_menu'] = query.data == "src_hookah_menu"
    
    hookah_note = ""
    if query.data != "src_hookah_menu":
        hookah_note = "\n\n⚠️ <b>Кальян</b> — доставляем только если он есть в вашем меню."
    
    safe_address = html.escape(context.user_data.get('address', ''))
    
    await query.edit_message_text(
        f"Отлично! Адрес: <b>{safe_address}</b>\n\n"
        f"Что будем заказывать? Выбери категорию 👇{hookah_note}",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

# ═══════════════════════════════════════════
# КАТЕГОРИИ
# ═══════════════════════════════════════════

async def category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cat_ps":
        await query.edit_message_text(
            "🎮 <b>PlayStation</b> — выбери что нужно:",
            parse_mode="HTML",
            reply_markup=ps_keyboard()
        )
        return PS_CHOICE
    
    elif query.data == "cat_hookah":
        has_menu = context.user_data.get('has_hookah_menu', False)
        note = "" if has_menu else "\n\n⚠️ <b>Внимание:</b> кальян доставляем только если он есть в вашем меню."
        await query.edit_message_text(
            f"💨 <b>Кальян и всё для него</b> — выбери:{note}",
            parse_mode="HTML",
            reply_markup=hookah_keyboard()
        )
        return HOOKAH_CHOICE
    
    elif query.data == "cat_tea":
        await query.edit_message_text(
            "🍵 <b>Чай</b> — напиши что именно хочешь:\n\n"
            "<i>(сорт, объём, количество персон — или просто напиши и мы подберём)</i>",
            parse_mode="HTML"
        )
        return TEA_CHOICE
    
    elif query.data == "cat_food":
        await query.edit_message_text(
            "🍔 <b>Еда и напитки</b> — напиши что хочешь:\n\n"
            "<i>(энергетики, соки, чипсы, шоколад, вода или индивидуальный заказ)</i>",
            parse_mode="HTML"
        )
        return FOOD_CHOICE
    
    elif query.data == "cat_done":
        return await show_cart(update, context)
    
    elif query.data == "back_category":
        await query.edit_message_text(
            "Выбери категорию 👇",
            reply_markup=category_keyboard()
        )
        return CATEGORY_CHOICE

# ═══════════════════════════════════════════
# PLAYSTATION СЕКЦИЯ
# ═══════════════════════════════════════════

async def ps_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_category":
        await query.edit_message_text("Выбери категорию 👇", reply_markup=category_keyboard())
        return CATEGORY_CHOICE
    
    item = query.data.replace("ps_", "")
    context.user_data['current_item'] = item
    context.user_data['current_price'] = PRICES.get(item, 0)
    
    await query.edit_message_text(
        f"На сколько дней нужен <b>{item}</b>? 📅",
        parse_mode="HTML",
        reply_markup=days_keyboard()
    )
    return PS_DAYS

async def ps_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "days_manual":
        await query.edit_message_text("Напиши количество дней цифрой 👇")
        context.user_data['waiting_days'] = 'ps'
        return PS_DAYS
    
    days = int(query.data.replace("days_", ""))
    
    item = context.user_data['current_item']
    price = context.user_data['current_price']
    total = price * days
    
    context.user_data['cart'].append({
        'name': item, 'days': days, 'price_per_day': price, 'total': total, 'type': 'ps'
    })
    
    await query.edit_message_text(
        f"✅ <b>{item}</b> на {days} дн. — <b>{total}₽</b> добавлен в заказ!\n\nДобавить ещё что-нибудь? 👇",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

async def ps_days_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Напиши просто число, например: 2")
        return PS_DAYS
        
    item = context.user_data['current_item']
    price = context.user_data['current_price']
    total = price * days
    
    context.user_data['cart'].append({
        'name': item, 'days': days, 'price_per_day': price, 'total': total, 'type': 'ps'
    })
    
    await update.message.reply_text(
        f"✅ <b>{item}</b> на {days} дн. — <b>{total}₽</b> добавлен!\n\nДобавить ещё? 👇",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

# ═══════════════════════════════════════════
# КАЛЬЯН СЕКЦИЯ
# ═══════════════════════════════════════════

async def hookah_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_category":
        await query.edit_message_text("Выбери категорию 👇", reply_markup=category_keyboard())
        return CATEGORY_CHOICE
    
    item = query.data.replace("hook_", "")
    context.user_data['current_item'] = item
    context.user_data['current_price'] = PRICES.get(item, 0)
    
    if item == "Кальян":
        await query.edit_message_text(
            f"На сколько дней нужен <b>{item}</b>? 📅",
            parse_mode="HTML",
            reply_markup=days_keyboard()
        )
        context.user_data['waiting_hookah_qty'] = False
        return HOOKAH_DAYS
    else:
        await query.edit_message_text(
            f"Сколько нужно <b>{item}</b>? Напиши количество 👇",
            parse_mode="HTML"
        )
        context.user_data['waiting_hookah_qty'] = True
        return HOOKAH_DAYS

async def hookah_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "days_manual":
        await query.edit_message_text("Напиши количество дней цифрой 👇")
        context.user_data['waiting_days'] = 'hookah'
        return HOOKAH_DAYS
    
    days = int(query.data.replace("days_", ""))
    item = context.user_data['current_item']
    price = context.user_data['current_price']
    total = price * days
    
    context.user_data['cart'].append({
        'name': item, 'days': days, 'price_per_day': price, 'total': total, 'type': 'hookah'
    })
    
    await query.edit_message_text(
        f"✅ <b>{item}</b> на {days} дн. — <b>{total}₽</b> добавлен!\n\nДобавить ещё? 👇",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

async def hookah_qty_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    item = context.user_data['current_item']
    price = context.user_data['current_price']
    
    if context.user_data.get('waiting_hookah_qty'):
        try:
            qty = int(text)
        except ValueError:
            await update.message.reply_text("Напиши просто число, например: 2")
            return HOOKAH_DAYS
        
        total = price * qty
        context.user_data['cart'].append({
            'name': item, 'qty': qty, 'price_each': price, 'total': total, 'type': 'hookah_supplies'
        })
        context.user_data['waiting_hookah_qty'] = False
    else:
        try:
            days = int(text)
        except ValueError:
            await update.message.reply_text("Напиши просто число дней, например: 2")
            return HOOKAH_DAYS
        
        total = price * days
        context.user_data['cart'].append({
            'name': item, 'days': days, 'price_per_day': price, 'total': total, 'type': 'hookah'
        })
    
    await update.message.reply_text(
        f"✅ <b>{item}</b> добавлен! — <b>{total}₽</b>\n\nДобавить ещё? 👇",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

# ═══════════════════════════════════════════
# ТЕКСТОВЫЙ ВВОД (ЧАЙ / ЕДА)
# ═══════════════════════════════════════════

async def tea_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['cart'].append({
        'name': f"Чай: {text}", 'total': 0, 'type': 'tea'
    })
    await update.message.reply_text(
        f"✅ <b>Чай</b> добавлен! Менеджер уточнит цену.\n\nДобавить ещё? 👇",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

async def food_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['cart'].append({
        'name': f"Еда/напитки: {text}", 'total': 0, 'type': 'food'
    })
    await update.message.reply_text(
        f"✅ Добавлено! Менеджер уточнит цену.\n\nДобавить ещё? 👇",
        parse_mode="HTML",
        reply_markup=category_keyboard()
    )
    return CATEGORY_CHOICE

# ═══════════════════════════════════════════
# КОРЗИНА И КОНЕЦ ЗАКАЗА
# ═══════════════════════════════════════════

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cart = context.user_data.get('cart', [])
    
    if not cart:
        msg = "Корзина пуста! Добавь хоть что-нибудь 👇"
        await query.edit_message_text(msg, reply_markup=category_keyboard())
        return CATEGORY_CHOICE
    
    cart_text = "🛒 <b>Твой заказ:</b>\n\n"
    total_sum = 0
    
    for item in cart:
        safe_item_name = html.escape(item['name'])
        if item['type'] == 'ps':
            cart_text += f"🎮 {safe_item_name} × {item['days']} дн. — <b>{item['total']}₽</b>\n"
            total_sum += item['total']
        elif item['type'] == 'hookah':
            cart_text += f"💨 {safe_item_name} × {item['days']} дн. — <b>{item['total']}₽</b>\n"
            total_sum += item['total']
        elif item['type'] == 'hookah_supplies':
            cart_text += f"🪨 {safe_item_name} × {item['qty']} шт. — <b>{item['total']}₽</b>\n"
            total_sum += item['total']
        elif item['type'] in ['tea', 'food']:
            cart_text += f"📦 {safe_item_name} — <i>цена уточняется</i>\n"
    
    prepayment = int(total_sum * PREPAYMENT_PERCENT / 100)
    cart_text += f"\n💰 <b>Итого: {total_sum}₽</b>"
    if prepayment > 0:
        cart_text += f"\n⚡ Предоплата 20%: <b>{prepayment}₽</b>"
        
    safe_address = html.escape(context.user_data.get('address', 'не указан'))
    safe_source = html.escape(context.user_data.get('source', 'не указан'))
    
    cart_text += f"\n📍 Адрес: {safe_address}"
    cart_text += f"\n📋 Источник: {safe_source}"
    
    context.user_data['total_sum'] = total_sum
    context.user_data['prepayment'] = prepayment
    
    await query.edit_message_text(cart_text, parse_mode="HTML", reply_markup=confirm_keyboard())
    return CONFIRM_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Заказ отменён. Напиши /start чтобы начать заново.")
        return START
    
    elif query.data == "confirm_edit":
        await query.edit_message_text("Что хочешь изменить? Выбери категорию 👇", reply_markup=category_keyboard())
        return CATEGORY_CHOICE
    
    elif query.data == "confirm_yes":
        order_id = get_order_id()
        user_data = context.user_data
        
        orders_db[order_id] = {
            'id': order_id,
            'user_id': user_data.get('user_id'),
            'username': user_data.get('username'),
            'address': user_data.get('address'),
            'source': user_data.get('source'),
            'cart': list(user_data.get('cart', [])),
            'total': user_data.get('total_sum', 0),
            'prepayment': user_data.get('prepayment', 0),
            'status': 'Новый'
        }
        
        safe_username = html.escape(user_data.get('username', ''))
        safe_address = html.escape(user_data.get('address', ''))
        safe_source = html.escape(user_data.get('source', ''))
        
        admin_msg = f"🔔 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n👤 Клиент: {safe_username}\n📍 Адрес: {safe_address}\n📋 Источник: {safe_source}\n\n🛒 <b>Состав:</b>\n"
        for item in user_data.get('cart', []):
            safe_name = html.escape(item['name'])
            if item['type'] == 'ps':
                admin_msg += f"🎮 {safe_name} × {item['days']} дн. — {item['total']}₽\n"
            elif item['type'] == 'hookah':
                admin_msg += f"💨 {safe_name} × {item['days']} дн. — {item['total']}₽\n"
            elif item['type'] == 'hookah_supplies':
                admin_msg += f"🪨 {safe_name} × {item['qty']} шт. — {item['total']}₽\n"
            elif item['type'] in ['tea', 'food']:
                admin_msg += f"📦 {safe_name} — цена уточняется\n"
        
        admin_msg += f"\n💰 <b>Итого: {user_data.get('total_sum', 0)}₽</b>\n⚡ Предоплата 20%: <b>{user_data.get('prepayment', 0)}₽</b>"
        
        if ADMIN_CHAT_ID and ADMIN_CHAT_ID != 0:
            try:
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение админу: {e}")
        else:
            logger.warning("Заказ оформлен, но ADMIN_CHAT_ID равен 0 или не задан. Сообщение не отправлено!")
        
        client_msg = f"✅ <b>Заказ #{order_id} принят!</b>\n\nНаш менеджер свяжется с тобой в ближайшее время.\n\n"
        if user_data.get('prepayment', 0) > 0:
            client_msg += f"⚡ <b>Предоплата 20% — {user_data.get('prepayment')}₽</b>\n\n"
        client_msg += f"📞 Срочные вопросы: {ADMIN_USERNAME}\n\nСпасибо за заказ! 🎉"
        
        await query.edit_message_text(client_msg, parse_mode="HTML", reply_markup=main_menu_keyboard())
        return START

# ═══════════════════════════════════════════
# СВОБОДНЫЕ ФУНКЦИИ (МЕНЮ)
# ═══════════════════════════════════════════

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    user_orders = [o for o in orders_db.values() if o.get('user_id') == uid]
    
    if not user_orders:
        text = "📋 У тебя пока нет заказов.\n\nОформи первый! 👇"
    else:
        text = "📋 <b>Твои заказы:</b>\n\n"
        for o in user_orders[-5:]:
            safe_address = html.escape(o['address'])
            text += f"<b>Заказ #{o['id']}</b> — {o['total']}₽ — {o['status']}\n📍 {safe_address}\n\n"
            
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    return START

async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    result = random.randint(1, 6)
    emojis = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
    
    text = f"🎲 Бросаю кубик...\n\nВыпало: <b>{emojis[result]} ({result})</b>!"
    if result == 6:
        text += "\n\n🔥 Шесть! Самое время оформить заказ 😄"
        
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    return START

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, пользуйся кнопками меню или командами /start и /menu.")
    return START

# ═══════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu_command),
        ],
        states={
            START: [CallbackQueryHandler(handle_main_menu, pattern="^(order|history|dice)$")],
            HOW_ARE_YOU: [MessageHandler(filters.TEXT & ~filters.COMMAND, how_are_you)],
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            GET_SOURCE: [CallbackQueryHandler(get_source, pattern="^src_")],
            CATEGORY_CHOICE: [
                CallbackQueryHandler(category_choice, pattern="^cat_"),
                CallbackQueryHandler(show_cart, pattern="^cat_done$"),
            ],
            PS_CHOICE: [CallbackQueryHandler(ps_choice, pattern="^(ps_|back_category$)")],
            PS_DAYS: [
                CallbackQueryHandler(ps_days, pattern="^days_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ps_days_text),
            ],
            HOOKAH_CHOICE: [CallbackQueryHandler(hookah_choice, pattern="^(hook_|back_category$)")],
            HOOKAH_DAYS: [
                CallbackQueryHandler(hookah_days, pattern="^days_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, hookah_qty_text),
            ],
            TEA_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tea_choice)],
            FOOD_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, food_choice)],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order, pattern="^confirm_")],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("menu", menu_command),
            MessageHandler(filters.TEXT, fallback)
        ],
        allow_reentry=True,
    )
    
    app.add_handler(conv_handler)
    logger.info("Бот успешно запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
