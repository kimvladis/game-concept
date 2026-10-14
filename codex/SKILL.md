---
name: game-concept
description: Use when the user wants a concept, reference image, mock screenshot or "how the game would look" picture for a 2D game idea, especially as a reference for $ref2game; triggers on "сделай концепт", "референс для игры", "нарисуй скриншот игры", "как выглядела бы игра", "game concept", "fake gameplay screenshot". Draws with the Codex session's built-in imagegen tool by default.
---

# Концепт-кадр 2D-игры

## Суть

Концепт — кадр из уже вышедшей игры: 16:9, игровая камера, HUD, герой посреди главного действия. ref2game
повторяет референс почти один в один (камеру, раскладку, палитру, масштаб, HUD), поэтому каждая деталь кадра — заказ
на будущую игру. Красивая иллюстрация без игры — плохой концепт.

Эталоны — `<skill>/examples/farm-flashlight.jpg` и `horde-shooter.jpg`: открой их через `view_image` перед первым
промптом.

## Codex

- `<skill>` — папка этого скилла. Скрипты запускай из корня проекта; пути с пробелами бери в кавычки.
- **Инструменты.** Спрашивай через `functions.request_user_input_async`, если он есть, иначе коротко в чате.
  Картинки открывай `view_image`, скрипты запускай `exec_command`, файлы правь `apply_patch`.
- **Генератор по умолчанию — встроенный imagegen сессии** (`image_gen__imagegen` / `image_gen.imagegen`, по его
  схеме): ключ не нужен, расходует лимиты Codex. `agy_gen.py` и `gemini_image.py` — только если они уже работают
  на машине (шаг 3). Вложенный Codex CLI и другие скиллы картинок не используй.
- **Параллельно и сабагенты.** Оба варианта генерируются одновременно (шаг 3). Слепую сверку надписей отдай
  сабагенту (`collaboration.spawn_agent`), если делегирование доступно; нет — сверяй сам.
- **Ход.** После конца хода Codex написать не может. Дождись обоих вариантов в этом же ходе, покажи их и спроси;
  «пришлю, когда догенерится» не обещай.
- **Python** с Pillow (`patch.py` нужен ещё NumPy). Если их нет, сделай окружение в проекте, системный Python
  не трогай.

## 1. Один раунд вопросов

Сначала проверь, какие генераторы есть кроме imagegen (ключ не печатай):

```bash
command -v agy; test -n "$GEMINI_API_KEY" && echo "GEMINI_API_KEY: env"; grep -q '^export GEMINI_API_KEY=' ~/.zshrc 2>/dev/null && echo "GEMINI_API_KEY: ~/.zshrc"
```

Одним вопросом (2–3 варианта, рекомендуемый первым) — только то, чего нет в идее:
- **камера:** 3/4 сверху, строго сбоку, изометрия 2:1;
- **стиль:** HD-пиксель, cel/ink с обводкой, расписной, плоский вектор…;
- **момент:** какой глагол игрока показать и чем он окупается;
- **генератор** — только если нашёлся `agy` или ключ: imagegen первым.

Остальное решай сам и назови решения в ответе. Пока ждёшь ответа, готовь то, что от него не зависит: папку
`concept/`, слоты промпта.

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

**Текст пиши.** Генераторы чисто рисуют короткие надписи и числа, а подписи HUD и числа делают из HUD правила игры:
«Energy», «84/100», «LV 7», «03:12». Надписи — 1–4 слова, на языке игры.

**Собираемо для ref2game:** 2D, одна проекция; 3–5 типов актёров (каждому нужен риг); предметы стоят отдельно;
эффекты — те, что пишутся кодом: свет, частицы, вспышки, взрывы, дождь.

Промпт каждой версии лежит рядом с ней: `concept/v1a.prompt.txt`.

## 3. Генерация

**imagegen** (по умолчанию):
- аргументы — `prompt` (текст из `concept/v1a.prompt.txt` дословно) и, для правок и эскизов пользователя,
  `referenced_image_paths` — абсолютные пути в порядке Image 1, Image 2…; `transparent_background` не нужен: кадр
  непрозрачный. Модель, seed, точный размер и путь сохранения не выдумывай;
- картинка есть только в чате — `num_last_images_to_include` вместо путей, не оба сразу;
- инструмент сам сохраняет файл (обычно в `$CODEX_HOME/generated_images/`). Бери путь, который он вернул, а не
  «самый свежий файл», и копируй: `cp "/returned/path.png" concept/v1a.png`;
- размер и пропорции выбирает инструмент: не растягивай и не увеличивай, фактический размер запиши в BRIEF. Если
  по краям кадра вышли полосы под 16:9, обрежь их;
- инструмент может переписать промпт: суди картинку по слотам, а не по тексту промпта. Насилие проси стилизованным,
  без крови; заблокированный промпт без изменений не повторяй.

**Скрипты** — если нашлись в шаге 1 и выбраны:

```bash
python3 <skill>/scripts/agy_gen.py      --prompt-file concept/v1a.prompt.txt --out concept/v1a.png --size 1920x1080 [REF ...]
python3 <skill>/scripts/gemini_image.py --prompt-file concept/v1a.prompt.txt --out concept/v1a.png --size 1920x1080 [REF ...]
```

У обоих скриптов одни флаги:
- **`agy_gen.py`** работает на подписке Antigravity (`agy`): ключ не нужен, расходует квоту, 40–90 с на картинку,
  выдаёт ~1376×768.
- **`gemini_image.py`** — платный Gemini API, Nano Banana 2.1. Нужен `GEMINI_API_KEY`. 15–40 с на картинку,
  выдаёт 2K (2752×1536) примерно за $0,07; весь концепт (2 варианта и 3–5 правок) обходится примерно в
  $0,3–0,5. Цена картинки печатается в последней строке вывода. Если ключ прописан в `~/.zshrc` позже старта
  оболочки, подгрузи его в той же команде: `eval "$(grep '^export GEMINI_API_KEY=' ~/.zshrc)"; python3 …`.
  Ключ не печатай.
- Обоим нужна сеть, а `agy` ещё пишет в `~/.gemini`. Если песочница не пускает, запроси запуск вне песочницы
  с коротким обоснованием.

Картинку не увеличивай: ref2game меряет в пикселях референса.
- **2 варианта сразу.** Они различаются по одному открытому вопросу (стиль, момент, камера), а не случайно.
  imagegen — два вызова параллельно, если инструмент это позволяет, иначе подряд без пауз. Скрипты — одной
  командой: `python3 … --out concept/v1a.png & python3 … --out concept/v1b.png & wait`.
- Покажи оба и по каждому — какие слоты вышли, какие нет. Пусть выберет (тем же вопросом, что в шаге 1).
- **Правка** выбранного: он же REF (`referenced_image_paths` у imagegen, позиционный REF у скриптов), промпт
  `Image 1 = the current concept. Keep everything else exactly; change only: <одно изменение>.` Одна правка — одно
  изменение. Версии: `v1a-e1.png`, `v1a-e2.png`…
- **После каждой генерации и правки сверь надписи по буквам** с промптом — на вырезках одной строки, увеличенных
  в 6–8 раз (Pillow, потом `view_image`): в целом кадре глаз дочитывает «как надо». Правка перерисовывает весь кадр
  и портит буквы там, где её не просили («ROCKS» → «ROCRS»). Сабагенту дай только вырезки, без промпта: пусть
  выпишет, что написано, буква в букву; с промптом сравни сам.
- **Испорченную надпись не чини промптом:** с «keep everything else» генератор сохраняет и ошибку (проверено дважды).
  Верни область из прошлой версии (раскладку правка обычно не сдвигает, а `patch.py` это проверяет):
  `python3 <skill>/scripts/patch.py --from v1a.png --into v1a-e1.png --box x0,y0,x1,y1 --out v1a-e1p.png`.
  Скрипт откажет, если вокруг рамки кадр поменялся или у версий разный размер. Ни в одной версии надпись не верна —
  оставь и запиши верный текст в BRIEF: HUD ref2game строит кодом.
- imagegen недоступен, а `agy` и ключа нет — отдай промпт пользователю: вставит в ChatGPT или приложение Gemini
  и положит картинку в `concept/`.

## 4. Сдача

В папку `concept/` нового проекта (не в чужой репозиторий):
- `final.png`, `final.prompt.txt`;
- `BRIEF.md`: жанр, кто игрок, главный глагол и отдача, угрозы, что значит каждый элемент HUD, стиль, камера,
  размер кадра, генератор (imagegen → Codex-редакция ref2game рисует им же; Antigravity → в Claude-редакции
  ref2game «подписка Antigravity»; `gemini_image.py` → «платный Gemini API, Nano Banana 2.1»).

Дальше `$ref2game` с `final.png` (в Claude Code — `/ref2game`): BRIEF отвечает на его вопросы шага 0.

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
| В `concept/` скопирован «самый свежий» файл из `generated_images` | Только путь, который вернул imagegen |
| «Варианты пришлю, когда догенерятся» | Codex не пишет после конца хода: дождись обоих в этом ходе |
