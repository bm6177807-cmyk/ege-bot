# handlers/states.py
from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    main = State()
    subject = State()
    subject_menu = State()
    theme = State()
    menu = State()
    answering = State()
    free_question = State()
    feedback = State()
    exam_settings = State()
    exam_question = State()
    hint_used = State()
    reminder_set = State()
    generate_task_confirm = State()
    exam_date_input = State()
    level_test = State()
    reaction_query = State()
    gift_user_input = State()  # для ввода ID получателя подарка
    # ─── инструменты предметов ───
    tool_geo_quiz = State()    # тренажёр «Страна–столица»
    tool_hist_cards = State()  # карточки дат
    tool_info_input = State()  # ввод числа для перевода систем счисления
    tool_bio_input = State()   # ввод генотипов для решётки Пеннета
    # ─── ежедневное задание ───
    daily_answering = State()
    # ─── мини-пробник ───
    mini_exam_question = State()