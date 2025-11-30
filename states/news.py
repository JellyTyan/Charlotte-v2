from aiogram.fsm.state import State, StatesGroup

class NewsSpamGroup(StatesGroup):
    news_spam = State()
    accept_news_spam = State()
