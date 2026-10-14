---
name: game-concept
description: Use when the user wants a concept, reference image, mock screenshot or "how the game would look" picture for a 2D game idea, especially as a reference for /ref2game; triggers on "сделай концепт", "референс для игры", "нарисуй скриншот игры", "как выглядела бы игра", "game concept", "fake gameplay screenshot".
---

# Концепт-кадр 2D-игры

## Суть

Концепт — кадр из уже вышедшей игры: 16:9, игровая камера, HUD, герой посреди главного действия. ref2game
повторяет референс почти один в один (камеру, раскладку, палитру, масштаб, HUD), поэтому каждая деталь кадра — заказ
на будущую игру. Красивая иллюстрация без игры — плохой концепт.

Эталоны — `<skill>/examples/farm-flashlight.jpg` и `horde-shooter.jpg`: посмотри их перед первым промптом.

## 1. Один раунд вопросов

Одним `AskUserQuestion` (2–4 варианта, рекомендуемый первым) — только то, чего нет в идее:
- **камера:** 3/4 сверху, строго сбоку, изометрия 2:1;
- **стиль:** HD-пиксель, cel/ink с обводкой, расписной, плоский вектор…;
- **момент:** какой глагол игрока показать и чем он окупается.

Остальное решай сам и назови решения в ответе.

## 2. Промпт: каждый слот обязателен

Английский, по шаблону. Пустой слот — дыра в будущей игре.

```
Gameplay screenshot of a released 2D indie game: <genre>. 16:9 frame with the in-game HUD.
CAMERA: <high 3/4 top-down | strict side view | isometric 2:1>, orthographic, one angle for every object
(buildings, props and characters alike); gameplay zoom that follows the player: characters about 1/10 of
the frame height, the hero larger than ordinary enemies unless it is a boss.
STYLE: <family; line weight and colour; shading; palette>.
WORLD: <place, time, weather>; <2-3 other actors or systems: NPCs, animals, pickups, crops...>;
<1-2 signs or decals with short text that set the tone>.
MOMENT: <hero> near the centre, <doing the core verb> at <target>; payoff: <effect> with a pop-up "<SHORT TEXT>".
THREAT: <enemies or hazard> on <side>; the safe area and the danger read apart at a glance.
LIGHT: <mood>; pools of light from <sources>.
HUD with crisp short English labels and numbers, inside panels at the edges:
top-left <resource bars with values>; top-right <time / day / level>;
bottom-centre <action slots whose icons are the player's verbs, the active one highlighted>.
FRAME: dark foreground silhouettes in two corners; open floor around the hero and between groups.
Not a poster, no title logo, no watermark, no perspective or vanishing point, no depth of field, no motion blur.
```

**Текст пиши.** Генераторы (Nano Banana, image_gen из Codex) чисто рисуют короткие надписи и числа, а подписи HUD и числа делают из HUD
правила игры: «Energy», «84/100», «LV 7», «03:12». Надписи — 1–4 слова, на языке игры.

**Собираемо для ref2game:** 2D, одна проекция; 3–5 типов актёров (каждому нужен риг); предметы стоят отдельно;
эффекты — те, что пишутся кодом: свет, частицы, вспышки, взрывы, дождь.

## 3. Генерация

```bash
python3 <skill>/scripts/agy_gen.py      --prompt-file concept/v1a.prompt.txt --out concept/v1a.png --size 1920x1080 [REF ...]
python3 <skill>/scripts/gemini_image.py --prompt-file concept/v1a.prompt.txt --out concept/v1a.png --size 1920x1080 [REF ...]
python3 <skill>/scripts/codex_gen.py    --prompt-file concept/v1a.prompt.txt --out concept/v1a.png --size 1920x1080 [REF ...]
```

У всех трёх скриптов одни флаги:
- **`agy_gen.py`** работает на подписке Antigravity (`agy`): ключ не нужен, расходует квоту, 40–90 с на картинку,
  выдаёт ~1376×768.
- **`gemini_image.py`** — платный Gemini API, Nano Banana 2.1. Нужен `GEMINI_API_KEY`. 15–40 с на картинку,
  выдаёт 2K (2752×1536) примерно за 7 центов; весь концепт (2 варианта и 3–5 правок) обходится примерно в
  30–50 центов. Цена картинки печатается в последней строке вывода. Если ключ прописан в `~/.zshrc` позже старта
  оболочки, подгрузи его в той же команде: `eval "$(grep '^export GEMINI_API_KEY=' ~/.zshrc)"; python3 …`.
  Ключ не печатай.
- **`codex_gen.py`** — встроенный image_gen из Codex CLI (`codex` в PATH, вход через `codex login`): ключ не нужен,
  расходует лимиты Codex, 2–3 мин на картинку. Размер выбирает сам инструмент, скрипт просит только ориентацию:
  16:9 выходит ~1672×941. `--model` задаёт модель агента Codex, а не картинки.

Если работает больше одного, добавь выбор генератора в вопрос из шага 1. Картинку не увеличивай: ref2game меряет в пикселях
референса.
- **2 варианта сразу**, каждый — отдельный запуск в фоне. Они различаются по одному открытому вопросу (стиль,
  момент, камера), а не случайно.
- Покажи их рядом и по каждому — какие слоты вышли, какие нет. Пусть выберет.
- **Правка** выбранного: он же REF, промпт `Image 1 = the current concept. Keep everything else exactly; change only: <одно изменение>.` Одна правка — одно изменение.
- **После каждой генерации и правки сверь надписи по буквам** с промптом — на вырезках одной строки, увеличенных
  в 6–8 раз: в целом кадре глаз дочитывает «как надо». Правка перерисовывает весь кадр и портит буквы там, где её
  не просили («ROCKS» → «ROCRS»).
- **Испорченную надпись не чини промптом:** с «keep everything else» генератор сохраняет и ошибку (проверено дважды).
  Верни область из прошлой версии — правка не сдвигает раскладку:
  `python3 <skill>/scripts/patch.py --from v1a.png --into v1a-e1.png --box x0,y0,x1,y1 --out v1a-e1p.png`.
  Скрипт откажет, если вокруг рамки кадр поменялся. Ни в одной версии надпись не верна — оставь и запиши верный
  текст в BRIEF: HUD ref2game строит кодом.
- Нет ни `codex`, ни `agy`, ни ключа — отдай промпт пользователю: вставит в приложение Gemini и положит картинку в `concept/`.

## 4. Сдача

В папку `concept/` нового проекта (не в чужой репозиторий):
- `final.png`, `final.prompt.txt`;
- `BRIEF.md`: жанр, кто игрок, главный глагол и отдача, угрозы, что значит каждый элемент HUD, стиль, камера,
  генератор (Antigravity → в ref2game «подписка Antigravity»; `gemini_image.py` → «платный Gemini API, Nano Banana 2.1»;
  `codex_gen.py` → «Codex built-in image_gen»).

Дальше `/ref2game` с `final.png`: BRIEF отвечает на его вопросы шага 0.

## Частые ошибки

| Ошибка | Как надо |
|---|---|
| HUD из одних иконок, «текст выйдет мусором» | Короткие подписи и числа: они и есть правила игры |
| Камера-карта: весь остров/уровень в кадре, герой — точка | Камера на игроке, персонажи ~1/10 высоты кадра |
| Здания сбоку, земля сверху; враги крупнее героя | Одна проекция для всего; масштаб героя задан словами |
| Герой просто стоит или идёт | Разгар глагола + отдача: эффект и всплывающая надпись |
| Мёртвый мир: только герой и враги | 2–3 других актёра или системы |
| Два одинаковых дубля «на удачу» | Варианты по открытому вопросу |
| После правки «всё на месте» без проверки | Каждую надпись — по буквам на увеличенной вырезке |
| «Исправь надпись на …» новой правкой | `patch.py` из версии, где надпись верна |
