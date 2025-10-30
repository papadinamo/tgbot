import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes


class FinanceBot:
    def __init__(self):
        self.data_file = 'finance_data.json'
        self.data = self.load_data()

    def load_data(self):
        return json.load(open(self.data_file, 'r')) if os.path.exists(self.data_file) else {}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get_user_data(self, user_id):
        if str(user_id) not in self.data:
            self.data[str(user_id)] = {'transactions': [], 'categories': {}, 'reminders': []}
        return self.data[str(user_id)]


bot = FinanceBot()


# Клавиатуры
def main_menu():
    buttons = [
        [InlineKeyboardButton("➕ Доход", callback_data="income"),
         InlineKeyboardButton("➖ Расход", callback_data="expense")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
         InlineKeyboardButton("💡 Советы", callback_data="tips")],
        [InlineKeyboardButton("⏰ Напоминания", callback_data="reminders")]
    ]
    return InlineKeyboardMarkup(buttons)


def reminders_menu():
    buttons = [
        [InlineKeyboardButton("➕ Добавить напоминание", callback_data="add_reminder")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back")]
    ]
    return InlineKeyboardMarkup(buttons)


def category_menu(type_):
    categories = ['еда', 'транспорт', 'развлечения', 'коммуналка', 'другое'] if type_ == 'expense' else ['зарплата',
                                                                                                         'подарок',
                                                                                                         'другое']
    buttons = [[InlineKeyboardButton(cat, callback_data=f"cat_{type_}_{cat}")] for cat in categories]
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)


# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Финансовый помощник\nУправляйте своими финансами:", reply_markup=main_menu())


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in ["income", "expense"]:
        await query.edit_message_text("Выберите категорию:", reply_markup=category_menu(data))
    elif data.startswith("cat_"):
        _, type_, category = data.split("_")
        context.user_data['input'] = {'type': type_, 'category': category}
        await query.edit_message_text(f"Введите сумму для {category}:")
    elif data == "stats":
        await show_stats(query)
    elif data == "tips":
        await show_tips(query)
    elif data == "reminders":
        await show_reminders(query)
    elif data == "add_reminder":
        context.user_data['waiting_reminder'] = True
        await query.edit_message_text("📝 Введите текст напоминания:")
    elif data == "back":
        await query.edit_message_text("Главное меню:", reply_markup=main_menu())


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if 'input' in context.user_data:
        try:
            amount = float(text)
            input_data = context.user_data['input']
            user_data = bot.get_user_data(user_id)

            transaction = {
                'amount': amount, 'category': input_data['category'],
                'type': input_data['type'], 'date': datetime.now().strftime("%d.%m %H:%M")
            }
            user_data['transactions'].append(transaction)

            if input_data['type'] == 'expense':
                user_data['categories'][input_data['category']] = user_data['categories'].get(input_data['category'],
                                                                                              0) + amount

            bot.save_data()
            await update.message.reply_text(f"✅ {amount}₽ добавлено!", reply_markup=main_menu())
            del context.user_data['input']
        except:
            await update.message.reply_text("❌ Введите число:")

    elif context.user_data.get('waiting_reminder'):
        user_data = bot.get_user_data(user_id)
        reminder = {
            'text': text,
            'date': datetime.now().strftime("%Y.%m.%d")
        }
        user_data['reminders'].append(reminder)
        bot.save_data()

        await update.message.reply_text("✅ Напоминание добавлено!", reply_markup=main_menu())
        del context.user_data['waiting_reminder']


async def show_stats(query):
    user_data = bot.get_user_data(query.from_user.id)
    transactions = user_data['transactions'][-10:]

    income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')

    text = f"📊 Статистика\n\n💰 Доходы: {income}₽\n💸 Расходы: {expense}₽\n⚖️ Баланс: {income - expense}₽\n\n"

    if user_data['categories']:
        text += "📈 Расходы по категориям:\n"
        for cat, amount in user_data['categories'].items():
            text += f"• {cat}: {amount}₽\n"

    await query.edit_message_text(text, reply_markup=main_menu())


async def show_tips(query):
    tips = [
        "💡 Ведите учет расходов ежедневно",
        "💡 Откладывайте 10-20% от дохода",
        "💡 Используйте правило 50/30/20",
        "💡 Анализируйте расходы каждую неделю"
    ]
    await query.edit_message_text("\n".join(tips), reply_markup=main_menu())


async def show_reminders(query):
    user_data = bot.get_user_data(query.from_user.id)
    text = "⏰ Ваши напоминания:\n\n"

    if user_data['reminders']:
        for reminder in user_data['reminders']:
            # Простой формат: текст(дата)
            text += f"• {reminder['text']}({reminder['date']})\n"
    else:
        text += "📭 Напоминаний нет\n\n"
        text += "Нажмите кнопку ниже чтобы добавить"

    await query.edit_message_text(text, reply_markup=reminders_menu())


async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_data = bot.get_user_data(update.effective_user.id)
        reminder = {
            'text': " ".join(context.args),
            'date': datetime.now().strftime("%Y.%m.%d")
        }
        user_data['reminders'].append(reminder)
        bot.save_data()
        await update.message.reply_text("✅ Напоминание добавлено!", reply_markup=main_menu())


def main():
    app = Application.builder().token("8432210308:AAEka9JZru55_GQE_3ovFwvwC_9oRkURAc8").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", add_reminder))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()