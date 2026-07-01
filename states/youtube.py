from aiogram.fsm.state import State, StatesGroup


class YouTubeStates(StatesGroup):
    choosing_mode = State()       # Choosing download parameters
    entering_time_range = State() # Entering range (e.g. 1:20-2:45)


class YouTubeDialogStates(StatesGroup):
    simple = State()
    balance = State()
    advanced = State()
    trim_input = State()

