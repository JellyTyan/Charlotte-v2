from aiogram.fsm.state import State, StatesGroup


class SavesStates(StatesGroup):
    rename_input = State()
