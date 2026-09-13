"""Сервис для работы с видео: случайное видео через YouTube Data API v3."""

import asyncio
import random
import re
import ssl
from typing import Any

import httpx

from app.config import settings

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# На машинах, где HTTPS-трафик фильтруется антивирусом/прокси, сертификат
# googleapis.com не проходит проверку по стандартному набору certifi.
# Доверяем системному хранилищу сертификатов Windows.
_ssl_context = ssl.create_default_context()

# YouTube search без параметра q возвращает пустой список результатов,
# поэтому каждый запрос идёт со случайным общим поисковым словом —
# это заодно даёт новый набор видео при каждом обращении.
# Запросы сгруппированы по категориям: при пополнении кэша берётся
# по одному запросу из РАЗНЫХ категорий — поэтому в кэше не оказываются
# сразу несколько близких тем (например, «гта 5» и «гта 5 трюки» вместе),
# и подряд не идут ролики одной тематики.
QUERY_TOPICS: dict[str, list[str]] = {
    "игры": [
        "майнкрафт", "майнкрафт выживание", "майнкрафт моды", "майнкрафт приколы",
        "ксго", "кс 2", "counter strike", "кс го трюки",
        "роблокс", "роблокс обби", "гта 5", "гта 5 трюки", "гта онлайн",
        "бравл старс", "бравл старс приколы", "standoff 2",
        "дота 2", "дота 2 приколы", "валорант", "фортнайт", "пабг",
        "апекс легенды", "геншин импакт", "сталкер", "элден ринг", "гаррис мод",
        "майнкрафт дроппер", "игры 2024", "летсплеи", "прохождение игр",
    ],
    "юмор и тикток": [
        "мемы", "мемы 2024", "тикток", "тикток тренды", "шортс", "смешные шортс",
        "приколы", "вайны", "челлендж", "пранки", "розыгрыши",
        "социальные эксперименты", "стендап", "комедия", "аниме",
    ],
    "музыка": [
        "рэп", "хип хоп", "новый рэп", "фонк", "фонк музыка",
        "электронная музыка", "драм энд бейс", "клубная музыка", "ремиксы",
        "новинки музыки", "концерт", "гитара", "фортепиано", "битбокс", "диджей",
    ],
    "спорт и экстрим": [
        "скейтборд", "скейт трюки", "сноуборд", "бмх", "паркур", "паркур трюки",
        "трюки на велосипеде", "воркаут", "турники", "фитнес",
        "бокс", "мма", "фридайвинг", "серфинг", "скайдайвинг",
    ],
    "авто и мото": [
        "авто", "дрифт", "драг рейсинг", "суперкары", "мотоциклы", "тюнинг",
        "ремонт авто", "тест драйв", "электрокары", "мото трюки",
    ],
    "технологии": [
        "гаджеты", "обзор смартфона", "айфон", "андроид", "пк сборка",
        "компьютеры", "технологии", "роботы", "нейросети",
        "искусственный интеллект", "3д печать", "дроны",
    ],
    "наука и природа": [
        "космос", "планеты", "чёрные дыры", "физика", "химия опыты",
        "эксперименты", "животные", "дикая природа", "коты", "собаки",
        "попугаи", "аквариумные рыбки", "океан", "вулканы", "молнии",
    ],
    "путешествия и выживание": [
        "путешествия", "туризм", "походы", "выживание", "бушкрафт",
        "выживание в лесу", "альпинизм", "рыбалка", "охота",
        "горы", "водопады", "города мира",
    ],
    "творчество и diy": [
        "diy", "лайфхаки", "рукоделие", "слайм", "оригами", "рисование",
        "3д ручка", "лепка", "резьба по дереву", "ремонт квартиры",
        "дизайн интерьера", "мебель своими руками",
    ],
    "еда": [
        "рецепты", "стритфуд", "фастфуд", "асмр еда", "мукбанг", "готовка",
        "выпечка", "пицца", "шашлык", "десерты",
    ],
    "история": [
        "история", "древние цивилизации", "тайны мира", "археология",
    ],
}

# Плоский список всех запросов (используется для проверок и подсчёта)
RANDOM_QUERIES = [q for variants in QUERY_TOPICS.values() for q in variants]

# Предварительная проверка встраиваемости через YouTube oEmbed
# (не требует API-ключа и не расходует квоту)
OEMBED_URL = "https://www.youtube.com/oembed"

# videos.list — батч-запрос длительностей: один вызов отдаёт длительность
# до 50 видео и стоит всего ~1 единицу квоты (поиск — 100)
VIDEOS_LIST_URL = "https://www.googleapis.com/youtube/v3/videos"

# --- Кэш кандидатов -------------------------------------------------------
#
# Поиск (search.list) стоит 100 единиц квоты за один вызов, а суточный
# лимит — 10 000 единиц. Чтобы квота не заканчивалась за 100 нажатий
# кнопки, результаты поиска складываются в кэш в памяти. Одно пополнение
# делает несколько разных поисков и раскладывает результаты по «корзинам»
# (отдельная корзина на поисковое слово) — при выдаче корзины перебираются
# по кругу, поэтому подряд не идут ролики на одну тему. Если квота
# исчерпана (ошибка 429) — продолжаем раздавать то, что осталось в кэше,
# и лишь когда пуст и кэш, возвращаем ошибку.

POOL_MIN_SIZE = 100  # пополнять кэш, когда суммарно кандидатов меньше этого числа
# (порог высокий специально: тогда новое пополнение подмешивает свежие темы,
# пока в кэше ещё много старых — в выдаче одновременно участвуют 6-15 тем)
REFILL_QUERIES_COUNT = 8  # сколько разных поисков делает одно пополнение
# (8 тем × 50 видео ≈ 400 кандидатов в кэше — в выдаче всегда смешаны
# ~8 разных категорий; квоты это почти не стоит: ~2 ед. на один клик)
KEY_DEAD_MINUTES = 30  # сколько минут не пробовать ключ с исчерпанной квотой

# Shorts — вертикальные ролики до 3 минут (актуальный лимит YouTube).
# Прямого признака «шортс» в API нет, поэтому режимы разделяются по точной
# длительности из videos.list, а поиск в режиме «шортсы» дополнительно
# идёт с тегом «#shorts» — в такой выдаче больше подходящих роликов.
SHORT_MAX_SECONDS = 180

# Порог пополнения кэша для режима: сколько подходящих кандидатов должно
# остаться, прежде чем делать новые поиски (шортсов в выдаче меньше)
MODE_POOL_MIN = {"all": POOL_MIN_SIZE, "video": 60, "shorts": 20}

# Режимы выборки
VIDEO_MODES = ("all", "video", "shorts")

# Корзины кандидатов: поисковое слово -> список видео этого поиска
_buckets: dict[str, list[dict[str, Any]]] = {}
_last_query: str | None = None  # из какой корзины выдали последнее видео
_seen_ids: set[str] = set()  # video_id, которые уже попадали в кэш
_pool_lock = asyncio.Lock()  # два запроса не должны пополнять кэш одновременно
_key_index: int = 0  # с какого ключа начинать следующий поиск (ротация)
_dead_keys: dict[int, float] = {}  # индекс ключа -> метка времени, когда можно снова пробовать


class YouTubeAPIError(Exception):
    """Базовая ошибка при работе с YouTube Data API."""


class YouTubeConfigError(YouTubeAPIError):
    """Ошибка конфигурации: ключ API не настроен."""


class YouTubeQuotaError(YouTubeAPIError):
    """Суточная квота YouTube API исчерпана."""


def _get_keys() -> list[str]:
    """Получить список всех ключей YouTube API."""
    keys = settings.youtube_keys
    if not keys:
        raise YouTubeConfigError(
            "YOUTUBE_API_KEY не настроен. Укажите ключ в файле backend/.env "
            "(см. backend/.env.example)."
        )
    return keys


def _extract_api_error(response: httpx.Response) -> str:
    """Достать понятное сообщение об ошибке из ответа YouTube API."""
    try:
        error = response.json().get("error", {})
        return error.get("message") or response.text
    except ValueError:
        return response.text


def _get_alive_key_index(keys: list[str]) -> int | None:
    """Вернуть индекс ключа, который можно использовать прямо сейчас.

    Пропускает ключи с недавно исчерпанной квотой (429) — они лежат
    в `_dead_keys` и не пробуются ещё KEY_DEAD_MINUTES минут.
    Ротация по кругу: начинает с `_key_index`, ищет первый живой.
    Если все ключи мертвы — вернёт None.
    """
    import time

    now = time.time()
    num_keys = len(keys)

    # Очистить ключи, у которых истекло время "мертвого" состояния
    for idx in list(_dead_keys.keys()):
        if now >= _dead_keys[idx]:
            del _dead_keys[idx]

    for offset in range(num_keys):
        idx = (_key_index + offset) % num_keys
        if idx not in _dead_keys:
            return idx

    return None  # все ключи мертвы


def _mark_key_dead(key_index: int) -> None:
    """Пометить ключ как исчерпавший квоту — не пробовать ещё KEY_DEAD_MINUTES минут."""
    import time

    _dead_keys[key_index] = time.time() + KEY_DEAD_MINUTES * 60


async def _is_embeddable(client: httpx.AsyncClient, video_id: str) -> bool:
    """Проверить, что видео разрешено встраивать на сторонние сайты.

    YouTube oEmbed отвечает 200 только для встраиваемых видео,
    для запрещённых — ошибкой (401/403/404).
    """
    response = await client.get(
        OEMBED_URL,
        params={
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "format": "json",
        },
    )
    return response.status_code == 200


# ISO-8601 длительность из contentDetails: PT1M2S, PT45S, PT1H2M3S, P1DT2H…
_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


def _parse_iso_duration(value: str) -> int | None:
    """Разобрать ISO-8601 длительность (PT1M2S -> 62 секунды)."""
    match = _ISO_DURATION_RE.match(value or "")
    if not match:
        return None
    parts = match.groupdict()
    total = (
        int(parts["days"] or 0) * 86400
        + int(parts["hours"] or 0) * 3600
        + int(parts["minutes"] or 0) * 60
        + float(parts["seconds"] or 0)
    )
    return int(total)


def _is_short(duration_seconds: int | None) -> bool:
    """Является ли ролик шортсом (по длительности)."""
    return duration_seconds is not None and duration_seconds <= SHORT_MAX_SECONDS


async def _fetch_durations(
    client: httpx.AsyncClient, video_ids: list[str]
) -> dict[str, int]:
    """Получить длительности видео одним батч-запросом videos.list.

    Один вызов обрабатывает до 50 видео и стоит ~1 единицу квоты.
    Возвращает {video_id: секунды}; при неудаче — что успели получить
    (кандидаты без длительности не попадут в режим «шортсы»).
    """
    durations: dict[str, int] = {}
    keys = _get_keys()
    ids = [video_id for video_id in video_ids if video_id]

    for start in range(0, len(ids), 50):
        chunk = ids[start : start + 50]

        # Перебираем ключи, как при поиске: 429 -> пробуем следующий
        for _attempt in range(len(keys)):
            alive_index = _get_alive_key_index(keys)
            if alive_index is None:
                return durations

            try:
                response = await client.get(
                    VIDEOS_LIST_URL,
                    params={
                        "part": "contentDetails",
                        "id": ",".join(chunk),
                        "key": keys[alive_index],
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = _extract_api_error(exc.response)
                if exc.response.status_code == 429 or "quota" in detail.lower():
                    _mark_key_dead(alive_index)
                    continue
                return durations
            except httpx.HTTPError:
                return durations

            for item in response.json().get("items", []):
                seconds = _parse_iso_duration(
                    item.get("contentDetails", {}).get("duration", "")
                )
                if seconds is not None:
                    durations[item.get("id", "")] = seconds
            break

    return durations


async def _refill_pool(
    client: httpx.AsyncClient, bias: str | None = None
) -> None:
    """Пополнить корзины кандидатов результатами нескольких разных поисков.

    Каждое пополнение делает REFILL_QUERIES_COUNT поисков по разным словам,
    в первую очередь с пустыми корзинами — так в кэше всегда есть видео
    разных тем. Ключи перебираются по кругу: если у одного ключа квота
    исчерпана, сразу пробуем следующий.

    Args:
        client: HTTP-клиент для запросов к YouTube API.
        bias: "shorts" — добавлять к каждому запросу тег «#shorts»,
            чтобы в выдаче было больше шортсов.

    Raises:
        YouTubeConfigError: если не настроен ни один ключ.
        YouTubeQuotaError: если квота исчерпана у всех ключей.
        YouTubeAPIError: если поиск не удался или не дал новых видео.
    """
    global _key_index

    keys = _get_keys()
    errors: list[str] = []

    # На холодный старт (кэш пуст) берём больше тем — 5 вместо 3, чтобы
    # разные темы были в выдаче с самого первого клика
    count = REFILL_QUERIES_COUNT + 2 if not _buckets else REFILL_QUERIES_COUNT

    # Один запрос из каждой РАЗНОЙ категории: близкие темы (варианты одной
    # категории) не попадают в одно пополнение — нет серий одинаковых роликов
    categories = list(QUERY_TOPICS.keys())
    random.shuffle(categories)
    queries: list[str] = []
    for cat in categories:
        if len(queries) >= count:
            break
        fresh = [v for v in QUERY_TOPICS[cat] if not _buckets.get(v)]
        queries.append(random.choice(fresh or QUERY_TOPICS[cat]))

    added = 0
    for q in queries:
        # Берём живой ключ (пропускаем те, у кого недавно исчерпана квота)
        alive_idx = _get_alive_key_index(keys)
        if alive_idx is None:
            errors.append("все ключи временно недоступны (квота исчерпана)")
            break

        key_number = alive_idx + 1  # номер ключа для сообщений (1-based)
        params = {
            "part": "snippet",
            "type": "video",
            "videoEmbeddable": "true",
            "maxResults": 50,
            # search без q возвращает пустой список; в режиме шортсов
            # добавляем тег — YouTube отдаёт больше коротких вертикальных
            "q": f"{q} #shorts" if bias == "shorts" else q,
            "key": keys[alive_idx],
        }

        try:
            response = await client.get(YOUTUBE_SEARCH_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_api_error(exc.response)
            if exc.response.status_code == 429 or "quota" in detail.lower():
                # Ключ исчерпал квоту — помечаем мёртвым на KEY_DEAD_MINUTES,
                # чтобы следующие 30 минут запросы шли через другие ключи
                _mark_key_dead(alive_idx)
                errors.append(f"у ключа #{key_number} исчерпана квота")
                continue
            raise YouTubeAPIError(
                f"YouTube API вернул ошибку {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            errors.append(f"ключ #{key_number} недоступен: {exc}")
            continue

        # Успех: следующий поиск пойдёт со следующего ключа —
        # квоты всех ключей расходуются равномерно
        _key_index = (alive_idx + 1) % len(keys)

        bucket: list[dict[str, Any]] = []
        for item in response.json().get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id or video_id in _seen_ids:
                continue

            snippet = item["snippet"]
            thumbnails = snippet.get("thumbnails", {})
            _seen_ids.add(video_id)
            bucket.append(
                {
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "description": snippet.get("description", ""),
                    "thumbnail_url": (
                        thumbnails.get("high", {}).get("url")
                        or thumbnails.get("medium", {}).get("url")
                        or thumbnails.get("default", {}).get("url", "")
                    ),
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

        if bucket:
            # Подтягиваем длительности батч-запросом (~1 ед. квоты на 50 видео):
            # без них невозможно отделить обычные ролики от шортсов
            durations = await _fetch_durations(
                client, [cand["video_id"] for cand in bucket]
            )
            for cand in bucket:
                cand["duration_seconds"] = durations.get(cand["video_id"])

            _buckets.setdefault(q, []).extend(bucket)
            added += len(bucket)

    if added == 0:
        if errors and all("квота" in e for e in errors):
            raise YouTubeQuotaError(
                f"Суточная квота YouTube API исчерпана для всех {len(keys)} ключей"
                + (f" ({'; '.join(errors)})" if errors else "")
                + ". Она восстановится ночью по тихоокеанскому времени "
                "(примерно в 10:00 по Москве)."
            )
        raise YouTubeAPIError(
            "YouTube API не вернул ни одного нового видео"
            + (f" ({'; '.join(errors)})" if errors else "")
        )


def _mode_candidates(mode: str) -> list[tuple[str, dict[str, Any]]]:
    """Собрать всех кандидатов кэша, подходящих под режим выборки."""
    pairs: list[tuple[str, dict[str, Any]]] = []
    for query, bucket in _buckets.items():
        for candidate in bucket:
            duration = candidate.get("duration_seconds")
            if mode == "shorts":
                # Без известной длительности нельзя гарантировать шортс
                if not _is_short(duration):
                    continue
            elif mode == "video":
                # В «обычные» попадает и неизвестная длительность (маловероятно,
                # что это шортс), зато гарантированно отсеиваются все шортсы
                if duration is not None and duration <= SHORT_MAX_SECONDS:
                    continue
            pairs.append((query, candidate))
    return pairs


def _remove_candidate(query: str, candidate: dict[str, Any]) -> None:
    """Убрать кандидата из его корзины (по идентичности объекта)."""
    bucket = _buckets.get(query)
    if not bucket:
        return
    for index, item in enumerate(bucket):
        if item is candidate:
            del bucket[index]
            return


async def get_random_youtube_video(mode: str = "all") -> dict[str, Any]:
    """Получить случайное видео через YouTube Data API v3.

    Кандидаты берутся из кэша в памяти (экономия квоты). Кэш разбит на
    «корзины» по поисковым запросам — видео выдаются из разных корзин
    случайно, поэтому подряд не идут ролики на одну тему. Каждый кандидат
    несёт точную длительность (videos.list), что позволяет отдавать только
    обычные ролики (mode="video") или только шортсы (mode="shorts").

    Перед показом кандидат проверяется через YouTube oEmbed: видео должно
    быть разрешено встраивать на сторонние сайты (иначе в iframe показалось
    бы «Видео недоступно»).

    Args:
        mode: "all" — любые видео, "video" — только обычные,
            "shorts" — только шортсы.

    Raises:
        YouTubeConfigError: если YOUTUBE_API_KEY не настроен.
        YouTubeQuotaError: если квота исчерпана у всех ключей и кэш пуст.
        YouTubeAPIError: если YouTube API недоступен или видео не найдены.
    """
    global _last_query

    if mode not in VIDEO_MODES:
        mode = "all"

    last_error: YouTubeAPIError | None = None

    # Две попытки пополнить кэш за один запрос (обычно хватает первой)
    for _ in range(2):
        if len(_mode_candidates(mode)) < MODE_POOL_MIN[mode]:
            async with _pool_lock:
                if len(_mode_candidates(mode)) < MODE_POOL_MIN[mode]:
                    try:
                        async with httpx.AsyncClient(
                            timeout=10, verify=_ssl_context
                        ) as client:
                            # В режиме шортсов поиск идёт с тегом #shorts —
                            # так в выдаче больше подходящих роликов
                            await _refill_pool(
                                client, bias="shorts" if mode == "shorts" else None
                            )
                    except YouTubeAPIError as exc:
                        # Например, квота исчерпана (429) — запоминаем ошибку
                        # и продолжаем раздавать остатки кэша
                        last_error = exc

        # Раздаём кандидатов (проверка oEmbed бесплатна). Абсолутная
        # случайность: перемешиваем всех подходящих кандидатов —
        # каждый клик независим и равновероят.
        async with httpx.AsyncClient(timeout=10, verify=_ssl_context) as client:
            matches = _mode_candidates(mode)
            random.shuffle(matches)
            for query, candidate in matches:
                if await _is_embeddable(client, candidate["video_id"]):
                    _remove_candidate(query, candidate)
                    _last_query = query
                    result = dict(candidate)
                    result.pop("duration_seconds", None)
                    result["is_short"] = _is_short(candidate.get("duration_seconds"))
                    return result
                # Не встраиваемое — выбрасываем и проверяем следующего
                _remove_candidate(query, candidate)

    if last_error is not None:
        raise last_error

    if mode == "shorts":
        raise YouTubeAPIError(
            "Не удалось найти шортс, разрешённый для встраивания. "
            "Попробуйте ещё раз."
        )
    raise YouTubeAPIError(
        "Не удалось найти видео, разрешённое для встраивания. Попробуйте ещё раз."
    )
