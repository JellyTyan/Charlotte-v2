from aiogram.fsm.state import State, StatesGroup


class YouTubeTrimStates(StatesGroup):
    waiting_start_time = State()
    waiting_end_time = State()
