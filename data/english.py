"""Английский язык для ЕГЭ."""

TASKS = {
    "english": {
        "en_1": {
            "name": "Лексика и словообразование",
            "tasks": [
                {
                    "id": "en_lex_1",
                    "text": "Choose the correct word: He made a great _____ to science.",
                    "options": ["contribution", "contribute", "contributor", "contributed"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "После глагола make используется существительное."
                },
                {
                    "id": "en_lex_2",
                    "text": "Выбери правильную форму: The company decided to _____ its operations.",
                    "options": ["expand", "expansion", "expansive", "expanded"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "После 'to' (инфинитива) используется базовая форма глагола."
                },
                {
                    "id": "en_lex_3",
                    "text": "Какое слово означает 'значительный, существенный'?",
                    "options": ["significant", "signify", "signature", "signal"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "Это прилагательное, образованное от латинского 'signum'."
                },
            ]
        },
        "en_2": {
            "name": "Грамматика (времена)",
            "tasks": [
                {
                    "id": "en_gr_1",
                    "text": "Choose the correct tense: By the time she arrived, he _____ the book.",
                    "options": ["had read", "has read", "read", "was reading"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "Действие завершилось ДО другого прошедшего действия → Past Perfect."
                },
                {
                    "id": "en_gr_2",
                    "text": "Выбери правильный вариант: While I _____ TV, the phone rang.",
                    "options": ["was watching", "watched", "have watched", "am watching"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "Длящееся действие в прошлом + прерывающее действие → Past Continuous."
                },
                {
                    "id": "en_gr_3",
                    "text": "Укажи правильную форму: She _____ in London since 2010.",
                    "options": ["has lived", "lived", "is living", "had lived"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "Действие началось в прошлом и продолжается сейчас + since → Present Perfect."
                },
            ]
        },
        "en_3": {
            "name": "Чтение и понимание текста",
            "tasks": [
                {
                    "id": "en_read_1",
                    "text": "The word 'ambiguous' most closely means:",
                    "options": ["unclear, having multiple meanings", "very clear", "dangerous", "important"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "'Ambi-' = два/двойной. Ambiguous = имеющий двойной смысл."
                },
                {
                    "id": "en_read_2",
                    "text": "Synonyms for 'enormous' are:",
                    "options": ["huge, vast, immense", "tiny, small, little", "fast, quick, rapid", "calm, quiet, silent"],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "Enormous = очень большой. Ищи синонимы размера."
                },
            ]
        },
        "en_4": {
            "name": "Устная часть / Темы",
            "tasks": [
                {
                    "id": "en_oral_1",
                    "text": "What is the main purpose of a 'topic sentence' in an essay paragraph?",
                    "options": [
                        "To introduce the main idea of the paragraph",
                        "To summarize the entire essay",
                        "To provide evidence for arguments",
                        "To describe specific details"
                    ],
                    "letters": ["A", "B", "C", "D"],
                    "correct": "A",
                    "hint": "Topic sentence = первое предложение абзаца, вводящее главную мысль."
                },
            ]
        },
    }
}

VIDEO_LINKS = {
    "english": {}
}
