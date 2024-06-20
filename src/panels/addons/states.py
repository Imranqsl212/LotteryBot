from aiogram.fsm.state import State, StatesGroup


class ExchangeTicketsStates(StatesGroup):
    waiting_for_tickets = State()


class DailyTicketsStates(StatesGroup):
    REQUESTED = State()


class AddBalance(StatesGroup):
    ID = State()
    AMOUNT = State()

class DEACREASE(StatesGroup):
    ID = State()
    AMOUNT = State()




class ModifyRaides(StatesGroup):
    SETIMAGE = State()
    SETTEXT = State()


class AdminStates(StatesGroup):
    EnteringWinningNumber = State()
    ChangingPrizeBank = State()
    AddingTaskChannel = State()


class ExchangeTickForLottery(StatesGroup):
    AMOUNT = State()

