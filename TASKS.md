# TASKS — bovidcars

## Этап 1. Инициализация
- [x] PRD-интервью (25.09.2026)
- [x] CLAUDE.md / TASKS.md / MEMORY.md / .gitignore
- [x] Контакты (contacts.txt → data/site.json)

## Этап 2. Данные первой партии (PDF 25.09.2026)
- [x] extract.py: текст и фото из 6 КП
- [x] JSON: Volvo EX90 Denim Blue (ID 13335424) — 73 000 €
- [x] JSON: Volvo EX90 Vapour Grey (YV1TFEVB2SG022136) — 73 000 €
- [x] JSON: Volvo EX90 Performance Platinum Grey (ID 12949182) — 73 000 €
- [x] JSON: Range Rover Sport Charente Grey (SAL1A2BW1TA660361) — 125 468 $
- [x] JSON: Range Rover Sport Ostuni Pearl White (SAL1A2BW5TA664980) — 126 327 $
- [x] JSON: Porsche Taycan 4S Cross Turismo (Q66902) — 143 391 €
- [x] Логотипы марок SVG
- [x] Таблица дополнений из официальных источников → утверждено

## Этап 3. Сборка
- [x] Тесты (validate, build, запрещённые строки)
- [x] validate.py, images.py, build.py, pdf.py
- [x] Шаблоны: каталог, страница авто, печать
- [x] Фильтры, переключатель €/$, «Поделиться»

## Этап 4. Превью и согласование
- [x] Показ в браузере, правки (hero без Грузии, цены € → $ без «≈», фото LR целиком)

## Этап 5. Публикация
- [x] Репозиторий iMark001/bovidcars + GitHub Pages → https://imark001.github.io/bovidcars/

## Этап 6. Code review
- [x] security-reviewer: CRITICAL/HIGH/MEDIUM нет
- [x] code-reviewer: HIGH — марка не проверялась → исправлено (validate + предупреждение в build)

## Этап 7. Память
- [x] MEMORY.md, авто-память

## Бэклог
- [ ] Официальные рендеры для Volvo Vapour Grey и Platinum Grey (в КП по 3 фото)
- [ ] (LOW) build: кэшировать Jinja Environment и метаданные фото при росте каталога
- [ ] (LOW) закрепить версии зависимостей (pip-compile)
