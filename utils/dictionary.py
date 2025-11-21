# utils/dictionary.py
import inspect
import pymorphy2

# --- ФИКС ДЛЯ PYTHON 3.11+ ---
if not hasattr(inspect, 'getargspec'):
    def _getargspec(func):
        spec = inspect.getfullargspec(func)
        return spec.args, spec.varargs, spec.varkw, spec.defaults
    inspect.getargspec = _getargspec
# -----------------------------

morph = pymorphy2.MorphAnalyzer()

# Список запрещенных слов
BAD_WORDS = {
    "сука", "хуй", "пизда", "бля", "блять", "ебать", "мудак", "пидор", 
    "гандон", "шлюха", "чмо", "жопа", "хер", "манда", "залупа", "говно", "залупка"
}

def check_word(word: str) -> dict:
    """
    Проверка слова:
    1. Не мат.
    2. Знакомое слово.
    3. Существительное (NOUN).
    Падеж больше не проверяем!
    """
    # 1. Проверка на мат
    if word in BAD_WORDS:
        return {'valid': False, 'error': "🤬 Не ругайся! Это слово запрещено."}

    # 2. Морфологический разбор
    parsed = morph.parse(word)
    best_parse = parsed[0]
    
    if not best_parse.is_known:
        return {'valid': False, 'error': "🤨 Я не знаю такого слова."}
    
    # 3. Проверка части речи
    if 'NOUN' not in best_parse.tag:
        pos = best_parse.tag.POS
        pos_map = {
            'VERB': 'глагол', 'INFN': 'глагол', 'ADJF': 'прилагательное',
            'ADJS': 'прилагательное', 'PRCL': 'частица', 'PREP': 'предлог',
            'CONJ': 'союз', 'INTJ': 'междометие', 'NPRO': 'местоимение'
        }
        pos_ru = pos_map.get(pos, 'не существительное')
        return {'valid': False, 'error': f"⚠️ Это {pos_ru}, а нужно <b>существительное</b> (кто? что?)."}
        
    # Проверка падежа удалена по просьбе

    return {'valid': True, 'error': None}