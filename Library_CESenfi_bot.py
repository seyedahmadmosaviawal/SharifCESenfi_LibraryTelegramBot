import sqlite3
import pandas as pd
import logging
import re
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update, Chat
from telegram.helpers import escape_markdown
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, ContextTypes, PicklePersistence
from collections import deque
import time
import os
from telegram.ext import ApplicationHandlerStop


# Logs:
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = 'Private'
OWNER_ID = 'Private'
FORWARDING_GROUP_ID = 'Private'
FORUM_GROUP_ID = 'Private'
NOTIFICATION_TOPIC_ID = 'Private'

DB_FILE = 'Private'
CSV_FILE = 'Private'
PERSISTENCE_FILE = os.path.join(os.getcwd(), 'bot_persistence.pickle')

SPAM_MESSAGE_LIMIT = 5
SPAM_TIME_WINDOW = 5
BAN_DURATION = 60

INITIAL_DUE_DATE = '15 بهمن'
EXTENSION_DUE_DATE = '15 تیر'
BUY_APPROVAL_MSG = "رسید مورد تایید است"
EXTENSION_APPROVAL_MSG = "تمدید با موفقیت صورت گرفت"
VERIFY_APPROVAL_MSG = "عکس مورد تایید است"


WAIT_FULL_NAME, WAIT_STUDENT_ID, MAIN_MENU, SEARCH_MENU, WAIT_SEARCH_BOOK, WAIT_SEARCH_AUTHOR, WAIT_BUY_NUMBER, WAIT_BUY_RECEIPT, WAIT_EXTENSION_BOOK_INDEX, WAIT_EXTENSION_RECEIPT, WAIT_EDIT_NAME, WAIT_EDIT_STUDENT_ID = range(12)

# Buttons
MAIN_BUTTONS = [['🔍 جستجو', '💳 امانت کتاب', '✏️ ویرایش اطلاعات'], ['📚 لیست همه کتاب‌ها', '❓ راهنما'], ['📜 آیین نامه', '🔁 تمدید کتاب']]
SEARCH_BUTTONS = [['🔍 جستجو بر اساس نویسنده', '🔍 جستجو بر اساس نام کتاب'], ['🔙 بازگشت به منوی اصلی']]

# Help message
HELP_TEXT = (
        "📚 *راهنمای استفاده از ربات کتابخانه*\n\n"
        "این ربات به شما امکان جستجو و امانت کتاب‌های کتابخانه را می‌دهد. در ادامه دستورات و نحوه استفاده توضیح داده شده است:\n\n"
        "📝 *ثبت‌نام*\n"
        "- برای شروع، دستور /start را وارد کنید.\n"
        "- نام و نام خانوادگی کامل خود را وارد کنید.\n"
        "- شماره دانشجویی خود را وارد کنید (شماره باید یکتا باشد).\n"
        "- در صورت وجود مشکل (مثل تکراری بودن شماره دانشجویی)، به این اکانت: @SenfiCE پیام بدهید.\n\n"
        "🔍 *جستجوی کتاب*\n"
        "- از منوی اصلی، گزینه 'جستجوی کتاب' را انتخاب کنید.\n"
        "- می‌توانید کتاب‌ها را بر اساس نام یا نویسنده جستجو کنید.\n"
        "- نتایج جستجو شامل نام، نویسنده، مترجم، انتشارات، شابک، تعداد موجود، مبلغ، کمد و طبقه است.\n\n"
        "💳 *امانت کتاب*\n"
        "- از منوی اصلی، گزینه 'امانت کتاب' را انتخاب کنید.\n"
        "- شماره کتاب (ID) که آن را از بخش جست‌و‌جو و یا بخش دیدن لیست همه‌ی کتاب‌ها گرفته‌اید وارد کنید.\n"
        "- رسید پرداخت را ارسال کنید.\n\n"
        "🔁 *تمدید کتاب*\n"
        "- از منوی اصلی، گزینه 'تمدید کتاب' را انتخاب کنید.\n"
        "- شماره کتاب امانت‌شده را وارد کنید.\n"
        "- رسید پرداخت برای تمدید را ارسال کنید.\n"
        "- پس از تأیید، مهلت تحویل به {EXTENSION_DUE_DATE} تغییر می‌کند.\n\n"
        "✏️ *ویرایش اطلاعات*\n"
        "- از منوی اصلی، گزینه 'ویرایش اطلاعات' را انتخاب کنید.\n"
        "- می‌توانید نام یا شماره دانشجویی خود را به‌روزرسانی کنید.\n\n"
        "📚 *لیست همه کتاب‌ها*\n"
        "با این دکمه می‌توانید لیست تمامی کتاب‌ها را به صورت دسته‌های ده‌تایی مشاهده کنید.\n\n"
        "📜 *آیین نامه*\n"
        "می‌توانید آیین‌نامه مربوط به امانت کمدها را دریافت کنید و با مفاد آن آشنا شوید که در زمان ارائه‌ی رسید برای امانت کتاب آن را تایید کنید.\n\n"
        "⚠️ *نکات مهم*\n"
        "- شماره دانشجویی باید یکتا باشد. در صورت بروز مشکل، به این اکانت:  @SenfiCE پیام بدهید.\n"
        "- کتاب‌های امانت‌شده باید تا تاریخ مقرر بازگردانده شوند و یا تمدید شوند.\n"
        "- برای هرگونه سؤال یا مشکل، به این اکانت (@SenfiCE) پیام بدهید."
    ).format(EXTENSION_DUE_DATE=EXTENSION_DUE_DATE)

REGULATIONS_TEXT = """
📜 آیین نامه امانت کتاب:
۱. هزینه کتاب برای امانت است، نه خرید کامل. در پایان مهلت امانت، *۸۰ درصد* از مبلغ پرداختی برگردانده میشود.
۲. مدت زمان امانت کتاب تا پایان ترم جاری است و از زمان تایید رسید است.
۳. در صورت تاخیر در بازگشت، به ازای هر روز تاخیر، جریمه نقدی به مقدار *۴ هزار تومان* اعمال خواهد شد.
۴. در صورت آسیب دیدن یا مفقود شدن کتاب، شخص امانت‌گیرنده موظف به پرداخت قیمت روز کتاب خواهد بود.
۵. کتاب‌ها باید به صورت فیزیکی و با هماهنگی قبلی به مسئولین صنفی دانشکده کامپیوتر تحویل داده شوند. که برای هماهنگی میتوانید به اکانت پشتیبانی صنفی دانشکده به نشانی @SenfiCE پیام بدهید.
"""

# Helper Functions:
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forwards any message received in a private chat to the designated group."""

    if update.message and update.message.chat.type == Chat.PRIVATE:
        try:
            user = update.message.from_user
            full_name_escaped = escape_markdown(user.full_name)
            user_info = f"👤 Message from: {full_name_escaped}"

            if user.username:
                username_escaped = escape_markdown(user.username)
                user_info += f" (@{username_escaped})"

            user_info += f"\n🆔 User ID: `{user.id}`"

            await context.bot.send_message(
                chat_id=FORWARDING_GROUP_ID,
                text=user_info,
                parse_mode='Markdown'
            )

            await context.bot.forward_message(
                chat_id=FORWARDING_GROUP_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logger.error(f"Failed to process or forward message for group {FORWARDING_GROUP_ID}: {e}")


async def increment_book_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی به این دستور را ندارید.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("فرمت: /increment_book_quantity <book_index>")
        return

    try:
        book_index = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ شاخص کتاب باید عدد باشد.")
        return

    book = get_book_by_index(book_index)
    if not book:
        await update.message.reply_text("❌ کتاب با این ID یافت نشد.")
        return

    try:
        update_quantity(book_index, book['quantity'] + 1)
        await update.message.reply_text(f"✅ تعداد کتاب (ID: {book_index}) با موفقیت افزایش یافت.")
    except Exception as e:
        logger.error(f"Failed to increment book quantity: {e}")
        await update.message.reply_text("❌ خطا در به‌روزرسانی تعداد کتاب. لطفاً بعداً امتحان کنید.")



async def remove_loan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی به این دستور را ندارید.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("فرمت: /remove_loan <book_index> <student_id>")
        return

    try:
        book_index = int(context.args[0])
        student_id = persian_to_english_digits(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ شاخص کتاب و شماره دانشجویی باید عدد باشند.")
        return

    retries = 5
    delay = 0.1
    conn = None
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            c = conn.cursor()

            c.execute("SELECT user_id FROM users WHERE student_id = ?", (student_id,))
            row = c.fetchone()
            if not row:
                await update.message.reply_text("❌ کاربر با این شماره دانشجویی یافت نشد.")
                return
            user_id = row[0]

            c.execute("SELECT loan_id FROM loans WHERE user_id = ? AND book_index = ?", (user_id, book_index))
            row = c.fetchone()
            if not row:
                await update.message.reply_text("❌ امانتی برای این کاربر و کتاب یافت نشد.")
                return
            loan_id = row[0]

            c.execute("DELETE FROM loans WHERE loan_id = ?", (loan_id,))
            conn.commit()

            await update.message.reply_text("✅ امانت کتاب از کاربر حذف شد.")

            try:
                book = get_book_by_index(book_index)
                book_name = book['name'] if book else f"کتاب با ID {book_index}"
                await context.bot.send_message(user_id, f"📚 کتاب شما ({book_name}, ID: {book_index}) با موفقیت بازگشت داده شد.")
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")

            return
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            else:
                await update.message.reply_text("❌ خطا در پایگاه داده. لطفاً بعداً امتحان کنید.")
                logger.error(f"Database error in remove_loan: {e}")
                return
        finally:
            if conn:
                conn.close()



def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''Private''')

    c.execute('''Private''')

    c.execute('''Private''')
    
    c.execute('''Private''')

    c.execute('''Private''')

    c.execute('''Private''')
    if c.fetchone()[0] == 0:
        # Private
        None
    conn.close()


def get_books():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("Private")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_book_by_index(index):
    retries = 5
    delay = 0.1
    conn = None
    for attempt in range(retries):
        # Private
        None


def get_user_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''Private''')
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user_data(user_id, full_name, student_id, username):
    retries = 5
    delay = 0.1
    conn = None
    for attempt in range(retries):
        # Private
        None


def update_user_info(user_id, full_name, student_id):
    retries = 5
    delay = 0.1
    conn = None
    for attempt in range(retries):
        # Private
        None


def register_loan(user_id, book_index, initial_price):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    loan_date = time.strftime('%Y-%m-%d %H:%M:%S')

    c.execute('''Private''')
    conn.commit()
    conn.close()

def get_user_eligible_loans(user_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''Private''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_loans_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''Private''')
    rows = c.fetchall()
    conn.close()

    formatted_data = []
    for row in rows:
        # Private
        None

    return formatted_data



def extend_loan(loan_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''Private''')
    conn.commit()
    conn.close()



def get_extension_flag():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''Private''')
    result = c.fetchone()
    conn.close()
    return result[0] == '1' if result else False


def toggle_extension_flag():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''Private''')
    result = c.fetchone()
    is_enabled = result and result[0] == '1'

    new_value = '0' if is_enabled else '1'

    c.execute('''Private''')

    conn.commit()
    conn.close()

    return new_value == '1'


def export_books_to_csv():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''Private''')
    rows = c.fetchall()
    conn.close()

    data = [
        'Private'
    ]

    csv_filename = 'Private'
    df = pd.DataFrame(data)
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    return csv_filename



def format_loan(loan, display_index):
    return f"{display_index}. *{loan['Private']}* (ID: {loan['Private']}) - قیمت امانت: {loan['Private']}, تاریخ بازگشت: {loan['Private']}"


async def toggle_extension(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی به این دستور را ندارید.")
        return

    new_status = toggle_extension_flag()
    status_text = "فعال" if new_status else "غیر فعال"
    await update.message.reply_text(f"✅ وضعیت *تمدید کتاب* به صورت *{status_text}* درآمد.", parse_mode='Markdown')


def normalize_isbn(isbn):
    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    isbn = str(isbn).translate(persian_to_english)
    isbn = ''.join(c for c in isbn if c.isdigit())
    return isbn


def format_book(book, display_index=None):
    prefix = f"{display_index}. " if display_index else ""
    return f"📚 {prefix}نام: {book['Private']}\n👤 نویسنده: {book['Private']}\n👤 مترجم: {book['Private']}\n🏢 انتشارات: {book['Private']}\n🔖 شابک: {book['Private']}\n📦 تعداد موجود: {book['Private']}\n💵 مبلغ(تومان): {book['Private']}"



def format_search_book(book, display_index=None):
    prefix = f"{display_index}. " if display_index else ""
    return f"{prefix}*{book['Private']}* (ID: {book['Private']}) - 💵 مبلغ: {book['Private']}, 📦 تعداد: {book['Private']}"

def persian_to_english_digits(text):
    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return text.translate(persian_to_english)

def is_student_id_unique(student_id, exclude_user_id=None):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    if exclude_user_id:
        c.execute('''Private''')
    else:
        c.execute('''Private''')
    result = c.fetchone()
    conn.close()
    return result is None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    context.user_data.clear()

    user_data = get_user_data(user_id)

    if user_data:
        reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
        await update.message.reply_text(f'😊 خوش آمدید، {user_data["full_name"]} عزیز! لطفاً گزینه‌ای انتخاب کنید.', reply_markup=reply_markup)
        return MAIN_MENU
    else:
        await update.message.reply_text('👋 خوش آمدید، برای شروع، لطفاً **نام و نام خانوادگی کامل** خود را وارد کنید:', parse_mode='MarkdownV2')
        return WAIT_FULL_NAME


async def export_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی به این دستور را ندارید.")
        return

    try:
        csv_filename = export_books_to_csv()
        await update.message.reply_document(
            document=open(csv_filename, 'rb'),
            caption=f"📚 گزارش کتاب‌های موجود در پایگاه داده تا تاریخ {time.strftime('%Y-%m-%d')}"
        )
        os.remove(csv_filename)
    except Exception as e:
        logger.error(f"Error in export_books: {e}")
        await update.message.reply_text("❌ خطایی در تهیه گزارش CSV رخ داد.")



async def wait_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    full_name = update.message.text.strip()
    if not full_name or full_name.isdigit():
        await update.message.reply_text('❌ لطفاً یک نام و نام خانوادگی معتبر وارد کنید.')
        return WAIT_FULL_NAME

    context.user_data['full_name'] = full_name
    await update.message.reply_text(f'✅ متشکرم، {full_name} عزیز، حالا لطفاً **شماره دانشجویی** خود را وارد کنید:', parse_mode='MarkdownV2')
    return WAIT_STUDENT_ID

async def wait_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    student_id = update.message.text.strip()
    student_id = persian_to_english_digits(student_id)

    if not student_id or not student_id.isdigit():
        await update.message.reply_text('❌ لطفاً یک شماره دانشجویی عددی معتبر وارد کنید.')
        return WAIT_STUDENT_ID

    if not is_student_id_unique(student_id):
        await update.message.reply_text(
            '❌ این شماره دانشجویی قبلاً ثبت شده است. اگر این شماره متعلق به شما نیست، لطفاً با اکانت @SenfiCE تماس بگیرید.\n'
            'لطفاً شماره دانشجویی دیگری وارد کنید:'
        )
        return WAIT_STUDENT_ID

    user = update.effective_user
    user_id = user.id
    username = user.username
    full_name = context.user_data.get('full_name')

    if not full_name:
        await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره /start را بزنید.')
        return ConversationHandler.END

    save_user_data(user_id, full_name, student_id, username)

    reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
    await update.message.reply_text(
        f'✅ ثبت‌نام شما با موفقیت انجام شد، {full_name} عزیز! لطفاً گزینه‌ای انتخاب کنید.',
        reply_markup=reply_markup
    )
    context.user_data.clear()
    return MAIN_MENU



async def default_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"Default handler triggered for user {update.effective_user.id}, current state: {context.user_data.get('conversation_state', 'None')}")
    reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
    await update.message.reply_text('😊 لطفاً از دکمه‌ها استفاده کنید یا /start را بزنید.', reply_markup=reply_markup)
    return MAIN_MENU



async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
    if text != '🔁 تمدید کتاب':
        context.user_data.clear()

    if text == '🔍 جستجو':
        reply_markup = ReplyKeyboardMarkup(SEARCH_BUTTONS, resize_keyboard=True)
        await update.message.reply_text('🔍 گزینه جستجو را انتخاب کنید:', reply_markup=reply_markup)
        return SEARCH_MENU
    elif text == '💳 امانت کتاب':
        await update.message.reply_text('💳 شماره کتاب (شاخص افزایشی و یا ID) را وارد کنید:', reply_markup=reply_markup)
        return WAIT_BUY_NUMBER
    elif text == '📚 لیست همه کتاب‌ها':
        await show_book_list(update, context, page=0)
        return MAIN_MENU
    elif text == '❓ راهنما':
        await update.message.reply_text(HELP_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        return MAIN_MENU
    elif text == '📜 آیین نامه':
        await update.message.reply_text(REGULATIONS_TEXT, reply_markup=reply_markup, parse_mode='Markdown')
        return MAIN_MENU
    elif text == '🔁 تمدید کتاب':
        return await extension_menu(update, context)
    elif text == '✏️ ویرایش اطلاعات':
        await update.message.reply_text('✏️ لطفاً نام و نام خانوادگی جدید خود را وارد کنید:')
        return WAIT_EDIT_NAME
    return MAIN_MENU


async def wait_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    full_name = update.message.text.strip()

    if not full_name or full_name.isdigit():
        await update.message.reply_text('❌ لطفاً یک نام و نام خانوادگی معتبر وارد کنید.')
        return WAIT_EDIT_NAME

    context.user_data['edit_full_name'] = full_name
    await update.message.reply_text('✅ حالا لطفاً شماره دانشجویی جدید خود را وارد کنید:')
    return WAIT_EDIT_STUDENT_ID


async def wait_edit_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    student_id = update.message.text.strip()
    student_id = persian_to_english_digits(student_id)

    if not student_id or not student_id.isdigit():
        await update.message.reply_text('❌ لطفاً یک شماره دانشجویی عددی معتبر وارد کنید.')
        return WAIT_EDIT_STUDENT_ID

    user_id = update.effective_user.id
    if not is_student_id_unique(student_id, exclude_user_id=user_id):
        await update.message.reply_text(
            '❌ این شماره دانشجویی قبلاً توسط کاربر دیگری ثبت شده است. اگر این شماره متعلق به شما است، لطفاً به اکانت @SenfiCE پیام بدهید.\n' \
            'در غیر این صورت لطفا شماره دانشجویی خودتان را وارد کنید.'
        )
        return WAIT_EDIT_STUDENT_ID

    full_name = context.user_data.get('edit_full_name')
    if not full_name:
        await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره شروع کنید.')
        return ConversationHandler.END

    update_user_info(user_id, full_name, student_id)

    await update.message.reply_text('✅ اطلاعات شما با موفقیت به‌روزرسانی شد.')
    context.user_data.clear()
    return await start(update, context)


async def extension_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_enabled = get_extension_flag()
    user_id = update.effective_user.id
    reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)

    if not is_enabled:
        await update.message.reply_text('❌ *حالا وقت تمدید کتاب‌ها نیست* و در پایان ترم جاری تمدیدها شروع می‌شوند.',
                                        reply_markup=reply_markup, parse_mode='Markdown')
        return MAIN_MENU

    active_loans = get_user_eligible_loans(user_id)

    if not active_loans:
        await update.message.reply_text('📚 شما در حال حاضر هیچ کتابی به امانت نگرفته‌اید.',
                                        reply_markup=reply_markup)
        return MAIN_MENU

    context.user_data['active_loans'] = active_loans

    loan_list_msg = '\n\n'.join([format_loan(loan, i+1) for i, loan in enumerate(active_loans)])

    await update.message.reply_text(
        f'📚 کتاب‌های امانتی شما:\n\n{loan_list_msg}\n\n'
        f'لطفاً **شماره ردیف کتاب** مورد نظر (مانند: 1 یا 2) را برای تمدید وارد کنید.',
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup([['/back']], resize_keyboard=True)
    )
    return WAIT_EXTENSION_BOOK_INDEX



async def forward_to_group_reciept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Private
    None


async def wait_extension_book_index(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == '/back':
        return await start(update, context)

    active_loans = context.user_data.get('active_loans', [])

    try:
        loan_number = int(text)
        if 1 <= loan_number <= len(active_loans):
            selected_loan = active_loans[loan_number - 1]
            book_index = selected_loan['book_index']
            book = get_book_by_index(book_index)

            # Extract numerical part of the price
            initial_price_str = book['price'].replace(',', '').replace(' ', '')
            initial_price = int(''.join(filter(str.isdigit, initial_price_str)))
            extension_price = int(initial_price * 0.20)

            context.user_data['extension_loan'] = selected_loan
            context.user_data['extension_price'] = extension_price

            card_number = '''Private'''
            commitment_text = "شما با فرستادن رسید پرداخت به آیین نامه تعهد داده اید که آن را میتوانید با استفاده از دکمه‌ی آیین نامه ببینید."

            await update.message.reply_text(
                f'🔁 **تمدید کتاب**\n\n'
                f'📚 کتاب: *{book["name"]}* (ID: {book_index})\n'
                f'💵 هزینه تمدید (۲۰٪): *{extension_price:,}* \n\n' # Format price with commas
                f'💳 لطفاً مبلغ فوق را به شماره کارت زیر به نام سیداحمد موسوی‌اول واریز کنید:\n'
                f'`\n{card_number}\n`\n'
                f'سپس رسید پرداخت را ارسال کنید (تصویر یا متن). یا برای بازگشت، /back را بزنید.\n\n'
                f'*{commitment_text}*',
                parse_mode='Markdown'
            )
            return WAIT_EXTENSION_RECEIPT
        else:
            await update.message.reply_text('❌ شماره ردیف نامعتبر است. لطفاً شماره ردیف را از لیست بالا انتخاب کنید.')
            return WAIT_EXTENSION_BOOK_INDEX
    except ValueError:
        await update.message.reply_text('❌ ورودی نامعتبر. لطفاً فقط شماره ردیف کتاب را وارد کنید.')
        return WAIT_EXTENSION_BOOK_INDEX


async def wait_extension_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text if update.message and update.message.text else ''
    if text == '/back':
        return await start(update, context)

    loan_data = context.user_data.get('extension_loan')
    extension_price = context.user_data.get('extension_price')
    if not loan_data or not extension_price:
        await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره /start را بزنید.')
        return MAIN_MENU

    user = update.message.from_user
    user_id = user.id
    username_display = f"@{escape_markdown(user.username)}" if user.username else f"User ID: {user_id}"

    try:
        await context.bot.forward_message(OWNER_ID, update.message.chat_id, update.message.message_id)
    except Exception as e:
        logger.error(f"Failed to forward receipt: {e}")

    data_tag = f"[EXTENSION_LOAN_ID:{loan_data['Private']}, USER_ID:{user_id}, BOOK_INDEX:{loan_data['Private']}, PRICE:{extension_price}]"

    info_text = (
        f"🔁 **درخواست تمدید کتاب** 🔁\n"
        f"👤 کاربر: {username_display}\n"
        f"🆔 آیدی: {user_id}\n"
        f"📚 کتاب (Loan ID: {loan_data['Private']}): {loan_data['Private']} (Book ID: {loan_data['Private']})\n"
        f"💵 مبلغ تمدید: {extension_price:,}\n\n"
        f"**\n-- اطلاعات پردازش ربات (حذف نشود) --\n"
        f"{data_tag}\n**"
        f"**جهت تایید تمدید، تنها با عبارت زیر پاسخ دهید:**\n`{EXTENSION_APPROVAL_MSG}`\n"
        f"**برای رد درخواست، دلیل رد را بنویسید.**"
    )

    try:
        await context.bot.send_message(OWNER_ID, info_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to send info text to admin: {e}")

    await update.message.reply_text('✅ رسید تمدید ارسال شد. منتظر تایید باشید.')

    context.user_data.pop('extension_loan', None)
    context.user_data.pop('extension_price', None)
    context.user_data.pop('active_loans', None)

    return MAIN_MENU


async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == '🔍 جستجو بر اساس نام کتاب':
        await update.message.reply_text('🔍 نام کتاب را وارد کنید:')
        return WAIT_SEARCH_BOOK
    elif text == '🔍 جستجو بر اساس نویسنده':
        await update.message.reply_text('🔍 نام نویسنده یا مترجم را وارد کنید:')
        return WAIT_SEARCH_AUTHOR
    elif text == '🔙 بازگشت به منوی اصلی':
        reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
        await update.message.reply_text('🔙 بازگشت به منوی اصلی.', reply_markup=reply_markup)
        context.user_data.clear()
        return MAIN_MENU
    return SEARCH_MENU


async def search_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.lower()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''Private''')
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    if not results:
        await update.message.reply_text('🔍 هیچ کتابی یافت نشد.', parse_mode='Markdown')
    else:
        msg = '\n\n'.join([format_search_book(book, display_index=i+1) for i, book in enumerate(results)])
        await update.message.reply_text(f'🔍 نتایج جستجو:\n\n{msg}', parse_mode='Markdown')
    return SEARCH_MENU

# Search by author/translator
async def search_author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.lower()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''Private''')
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    if not results:
        await update.message.reply_text('🔍 هیچ کتابی یافت نشد.', parse_mode='Markdown')
    else:
        msg = '\n\n'.join([format_search_book(book, display_index=i+1) for i, book in enumerate(results)])
        await update.message.reply_text(f'🔍 نتایج جستجو:\n\n{msg}', parse_mode='Markdown')
    return SEARCH_MENU

# Buy: Wait for number
async def wait_buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    main_menu_options = {'🔍 جستجو', '💳 امانت کتاب', '📚 لیست همه کتاب‌ها', '❓ راهنما', '📜 آیین نامه'}
    if text in main_menu_options:
        return await main_menu(update, context)

    try:
        index = int(text)
        book = get_book_by_index(index)
        if not book:
            await update.message.reply_text('❌ شماره نامعتبر.')
            return WAIT_BUY_NUMBER
        if book['Private'] <= 0:
            await update.message.reply_text('📦 موجودی تمام شده.')
            return WAIT_BUY_NUMBER
        context.user_data['Private'] = book
        card_number = "Private"


        commitment_text = "شما با فرستادن رسید پرداخت به آیین نامه تعهد داده اید که آن را میتوانید با استفاده از دکمه‌ی آیین نامه ببینید."

        await update.message.reply_text(
            f'{format_book(book)}\n\n'
            f'💳 لطفاً مبلغ {book["price"]}  تومان به شماره کارت زیر به نام سیداحمد موسوی‌اول واریز کنید:\n'
            f'`\n{card_number}\n`\n'
            f'سپس رسید پرداخت را ارسال کنید (تصویر یا متن). یا برای بازگشت، /back را بزنید.\n\n'
            f'*{commitment_text}*',
            parse_mode='Markdown'
        )
        return WAIT_BUY_RECEIPT
    except ValueError:
        await update.message.reply_text('❌ شماره معتبر وارد کنید.')
        return WAIT_BUY_NUMBER


async def wait_buy_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text if update.message and update.message.text else ''
    main_menu_options = {'🔍 جستجو', '💳 امانت کتاب', '📚 لیست همه کتاب‌ها', '❓ راهنما', '📜 آیین نامه'}
    if text in main_menu_options:
        return await main_menu(update, context)

    if text == '/back':
        reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
        await update.message.reply_text('🔙 بازگشت به منوی اصلی.', reply_markup=reply_markup)
        context.user_data.clear()
        return MAIN_MENU

    book = context.user_data.get('buy_book')
    if not book:
        return MAIN_MENU

    user = update.message.from_user
    user_id = user.id


    username_display = f"@{escape_markdown(user.username)}" if user.username else f"User ID: {user_id}"

    try:
        await context.bot.forward_message(OWNER_ID, update.message.chat_id, update.message.message_id)
        logger.info(f"Forwarded receipt from {update.effective_chat.id} to admin {OWNER_ID}")
    except Exception as e:
        logger.error(f"Failed to forward receipt: {e}")

    data_tag = f"[BUY_INDEX:{book['Private']}, USER_ID:{user_id}, PRICE:{book['Private']}]"
    info_text = (
        f"👤 کاربر: {username_display}\n"
        f"🆔 آیدی: {user_id}\n"
        f"📖 کتاب: {book['Private']} (ID: {book['Private']})\n"
        f"💵 مبلغ: {book['Private']}\n\n"
        f"**\n-- اطلاعات پردازش ربات (حذف نشود) --\n"
        f"{data_tag}\n**"
        f"**جهت تایید، تنها با عبارت زیر پاسخ دهید:**\n`{BUY_APPROVAL_MSG}`\n"
        f"**برای رد درخواست، دلیل رد را بنویسید.**"
    )

    try:
        # Send the info text as a separate message
        await context.bot.send_message(OWNER_ID, info_text, parse_mode='Markdown')
        logger.info(f"Sent info text with data tag to admin {OWNER_ID}")
    except Exception as e:
        logger.error(f"Failed to send info text to admin: {e}")

    await update.message.reply_text('✅ رسید ارسال شد. منتظر تایید باشید.')
    del context.user_data['buy_book']
    return MAIN_MENU


# Update quantity
def update_quantity(index, new_quantity):
    retries = 5
    delay = 0.1
    conn = None
    for attempt in range(retries):
        # Private
        None


async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Private
    None


# Async Command Handler: show_books_used
async def show_books_used(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔️ دسترسی محدود است.")
        return

    try:
        data = get_all_loans_data()

        if not data:
            await update.message.reply_text("❌ در حال حاضر هیچ کتابی در امانت نیست.")
            return

        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)
        csv_filename = 'books_in_use_report.csv'
        # Using 'utf-8-sig' ensures Persian characters display correctly in Excel
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

        # Send the CSV file
        await update.message.reply_document(
            document=open(csv_filename, 'rb'),
            caption=f"گزارش کامل کتاب‌های امانت رفته تا تاریخ {time.strftime('%Y-%m-%d')}"
        )

        # Clean up the file
        os.remove(csv_filename)

    except Exception as e:
        logger.error(f"Error in show_books_used: {e}")
        await update.message.reply_text("❌ خطایی در تهیه گزارش CSV رخ داد.")


# Add new function to get due loans grouped by user
def get_due_loans_by_user():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Get loans where expires_date = '1 بهمن', join with books and users
    c.execute('''Private''')
    rows = c.fetchall()
    conn.close()

    from collections import defaultdict
    due_loans = defaultdict(list)
    for row in rows:
        # Private
        None
    return due_loans


# Add new admin command: remind_due_books
async def remind_due_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی به این دستور را ندارید.")
        return

    due_loans = get_due_loans_by_user()

    if not due_loans:
        await update.message.reply_text("✅ هیچ کتابی با مهلت '1 بهمن' یافت نشد.")
        return

    sent_count = 0
    for user_id, loans in due_loans.items():
        # Format message
        book_list = '\n'.join([f"- {loan['Private']} (ID: {loan['Private']})" for loan in loans])
        message = (
            f"📚 سلام {loans[0]['Private']} عزیز،\n"
            f"کتاب‌های زیر با مهلت تحویل '1 بهمن' در امانت شما هستند:\n"
            f"{book_list}\n\n"
            f"لطفاً برای تحویل یا تمدید کتاب اقدام کنید. برای تمدید از دکمه '🔁 تمدید کتاب' استفاده کنید."
        )

        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send reminder to user {user_id}: {e}")

    await update.message.reply_text(f"✅ یادآوری به {sent_count} کاربر ارسال شد.")


# Show paginated book list
async def show_book_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    books = get_books()
    per_page = 10
    start = page * per_page
    end = min(start + per_page, len(books))
    page_books = books[start:end]

    if not page_books:
        await update.message.reply_text('📚 هیچ کتابی نیست.')
        return

    msg = '\n\n'.join([format_book(book, display_index=start + i + 1) for i, book in enumerate(page_books)])

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton('⬅️ صفحه قبلی', callback_data=f'list_prev_{page}'))
    if end < len(books):
        buttons.append(InlineKeyboardButton('➡️ صفحه بعدی', callback_data=f'list_next_{page}'))

    reply_markup = InlineKeyboardMarkup([buttons])
    if update.callback_query:
        await update.callback_query.edit_message_text(f'📚 لیست کتاب‌ها (صفحه {page + 1}):\n\n{msg}', reply_markup=reply_markup)
    else:
        await update.message.reply_text(f'📚 لیست کتاب‌ها (صفحه {page + 1}):\n\n{msg}', reply_markup=reply_markup)

# Callback for list buttons
async def list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    logger.info(f"Callback triggered for user {update.effective_user.id}, data: {data}")

    if data == 'list_back':
        reply_markup = ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True)
        await query.edit_message_text('🔙 بازگشت به منوی اصلی.', reply_markup=reply_markup)
        context.user_data.clear()
        return MAIN_MENU
    elif 'prev' in data:
        page = int(data.split('_')[2]) - 1
        await show_book_list(update, context, page)
    elif 'next' in data:
        page = int(data.split('_')[2]) + 1
        await show_book_list(update, context, page)
    return MAIN_MENU

# Spam checker
async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    user_id = user.id

    if user_id == OWNER_ID:
        return

    current_time = time.time()

    if 'banned_users' not in context.bot_data:
        context.bot_data['Private'] = {}
    if 'message_timestamps' not in context.bot_data:
        context.bot_data['Private'] = {}

    banned_users = context.bot_data['Private']

    if user_id in banned_users:
        ban_expires_at = banned_users[user_id]
        if current_time < ban_expires_at:
            remaining_time = int(ban_expires_at - current_time)
            text = f"❗️ شما به دلیل ارسال پیام‌های زیاد مسدود شده‌اید. لطفاً {remaining_time} ثانیه دیگر دوباره امتحان کنید."

            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text)
            raise ApplicationHandlerStop
        else:
            del banned_users[user_id]

    message_timestamps = context.bot_data['Private']
    if user_id not in message_timestamps:
        message_timestamps[user_id] = deque(maxlen=SPAM_MESSAGE_LIMIT)

    user_timestamps = message_timestamps[user_id]
    user_timestamps.append(current_time)

    if len(user_timestamps) == SPAM_MESSAGE_LIMIT:
        if (user_timestamps[-1] - user_timestamps[0]) < SPAM_TIME_WINDOW:
            banned_users[user_id] = current_time + BAN_DURATION
            text = f"🚫 شما به دلیل ارسال پیام‌های زیاد به مدت {BAN_DURATION} ثانیه مسدود شدید."

            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text)
            user_timestamps.clear()
            raise ApplicationHandlerStop

def main():
    init_db()
    logger.info(f"Attempting to load persistence from {PERSISTENCE_FILE}")
    try:
        persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
        logger.info("Persistence loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load persistence: {e}. Starting fresh.")
        persistence = None

    application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # REGISTRATION STATES
            WAIT_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_full_name)],
            WAIT_STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_student_id)],

            # MAIN BOT STATES
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            SEARCH_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_menu)],
            WAIT_SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_book)],
            WAIT_SEARCH_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_author)],
            WAIT_BUY_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_buy_number)],
            WAIT_BUY_RECEIPT: [MessageHandler(filters.ALL & ~filters.COMMAND, wait_buy_receipt)],

            # Add to conv_handler states
            WAIT_EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_edit_name)],
            WAIT_EDIT_STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_edit_student_id)],

            # NEW EXTENSION STATES
            WAIT_EXTENSION_BOOK_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_extension_book_index)],
            WAIT_EXTENSION_RECEIPT: [MessageHandler(filters.ALL & ~filters.COMMAND, wait_extension_receipt)],
        },
        fallbacks=[CommandHandler('start', start), CommandHandler('back', start), MessageHandler(filters.Regex('^(🔍 جستجو|💳 امانت کتاب|📚 لیست همه کتاب‌ها|❓ راهنما|📜 آیین نامه|🔁 تمدید کتاب|🔙 بازگشت به '
                                                                                                            'منوی اصلی)$'), main_menu)],
        per_user=True,
        per_chat=True
    )

    # MODIFICATION: We will organize handlers into groups for guaranteed execution order.

    # Group -2: Admin Commands (Must run before conversation handler)
    application.add_handler(CommandHandler('toggle_extension', toggle_extension), group=-2)
    application.add_handler(CommandHandler('show_books_used', show_books_used), group=-2)
    application.add_handler(CommandHandler('remind_due_books', remind_due_books), group=-2)
    application.add_handler(CommandHandler('export_books', export_books), group=-2)
    application.add_handler(CommandHandler('increment_book_quantity', increment_book_quantity), group=-2)
    application.add_handler(CommandHandler('remove_loan', remove_loan), group=-2)

    # Group -1: Spam checking (runs first)
    application.add_handler(MessageHandler(filters.ALL, check_spam), group=-1)
    application.add_handler(CallbackQueryHandler(check_spam), group=-1)

    # Group 0: Message forwarding (runs second)
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, forward_to_group), group=0)
    application.add_handler(MessageHandler(
    filters.ALL & filters.ChatType.PRIVATE & ~filters.Chat(chat_id=FORUM_GROUP_ID),
    forward_to_group_reciept
), group=0)

    # Group 1: Main bot logic (runs third)
    application.add_handler(MessageHandler(filters.REPLY & filters.User(user_id=OWNER_ID), handle_owner_reply), group=1)
    application.add_handler(conv_handler, group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, default_handler), group=1)
    application.add_handler(CallbackQueryHandler(list_callback, pattern='^list_'), group=1)

    application.run_polling()

if __name__ == '__main__':
    main()