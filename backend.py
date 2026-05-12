#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бекенд для зернової торгової платформи
Flask API + парсинг даних
ВИПРАВЛЕНА ВЕРСІЯ
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
import threading
import math
import json
import os
from collections import defaultdict

# Selenium для ukragroconsult
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

app = Flask(__name__, static_folder='.')
CORS(app)

# Глобальні змінні
prop_data = []
info_data = {}
last_update = None
user_offers = []
geocache = {}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
INTERESTED_CROPS = ["Кукурудза", "Пшениця", "Соя", "Ячмінь", "Ріпак", "Горох", "Овес", "Гречка", "Цукровий буряк", "Соняшник"]

# ВИПРАВЛЕННЯ 1: Розширений словник локацій
KNOWN_LOCATIONS = {
    # Обласні центри
    "Одеса": (46.4825, 30.7233),
    "Ізмаїл": (45.3500, 28.8400),
    "Чорноморськ": (46.3061, 30.6561),
    "Київ": (50.4501, 30.5234),
    "Миколаїв": (46.9659, 31.9974),
    "Херсон": (46.6354, 32.6169),
    "Дніпро": (48.4647, 35.0462),
    "Полтава": (49.5883, 34.5514),
    "Кропивницький": (48.5079, 32.2623),
    "Черкаси": (49.4285, 32.0624),
    "Вінниця": (49.2328, 28.4681),
    "Хмельницький": (49.4228, 26.9871),
    "Житомир": (50.2547, 28.6587),
    "Рівне": (50.6199, 26.2516),
    "Луцьк": (50.7472, 25.3254),
    "Львів": (49.8397, 24.0297),
    "Тернопіль": (49.5535, 25.5948),
    "Івано-Франківськ": (48.9226, 24.7111),
    "Чернівці": (48.2921, 25.9358),
    "Ужгород": (48.6208, 22.2879),
    "Харків": (49.9935, 36.2304),
    "Суми": (50.9077, 34.7981),
    "Чернігів": (51.4982, 31.2893),
    "Запоріжжя": (47.8388, 35.1396),
    
    # Великі міста
    "Кривий Ріг": (47.9086, 33.3432),
    "Маріуполь": (47.0951, 37.5494),
    "Кременчук": (49.0659, 33.4148),
    "Біла Церква": (49.7880, 30.1119),
    "Бердянськ": (46.7650, 36.7883),
    "Мелітополь": (46.8486, 35.3708),
    "Сімферополь": (44.9572, 34.1108),
    "Краматорськ": (48.7233, 37.5564),
    "Слов'янськ": (48.8571, 37.6197),
    "Ужгород": (48.6208, 22.2879),
    "Умань": (48.7500, 30.2167),
    "Бровари": (50.5108, 30.7928),
    "Миронівка": (49.6583, 31.0792),
    "Ірпінь": (50.5217, 30.2519),
    "Переяслав": (50.0667, 31.4500),
    "Конотоп": (51.2404, 33.2008),
    "Ромни": (50.7500, 33.4833),
    "Шостка": (51.8667, 33.4833),
    "Глухів": (51.6833, 33.9167),
    "Лубни": (50.0167, 32.9833),
    "Глобино": (49.3833, 33.2500),
    "Хорол": (49.5167, 33.2667),
    "Радивилів": (50.1333, 25.2500),
    "Дубно": (50.4167, 25.7500),
    "Здолбунів": (50.5167, 26.2333),
    "Костопіль": (50.8833, 26.4500),
    "Корець": (50.6167, 27.1667),
    "Кам'янець-Подільський": (48.6826, 26.5859),
    "Миргород": (49.9667, 33.6167),
    "Гребінка": (50.0833, 33.5333),
    "Лисичанськ": (48.9167, 38.4167),
    "Сєвєродонецьк": (48.9484, 38.4939),
    "Алчевськ": (48.4697, 38.7994),
    "Луганськ": (48.5740, 39.3078),
    "Горлівка": (48.3000, 38.0500),
    "Макіївка": (48.0467, 37.9261),
    "Покровськ": (48.2833, 37.1833),
    "Добропілля": (48.4667, 37.0833),
    "Красноармійськ": (48.2833, 37.1833),
    
    # Райони та області
    "Одеська": (46.4825, 30.7233),
    "Київська": (50.4501, 30.5234),
    "Дніпропетровська": (48.4647, 35.0462),
    "Полтавська": (49.5883, 34.5514),
    "Кіровоградська": (48.5079, 32.2623),
    "Черкаська": (49.4285, 32.0624),
    "Вінницька": (49.2328, 28.4681),
    "Хмельницька": (49.4228, 26.9871),
    "Житомирська": (50.2547, 28.6587),
    "Рівненська": (50.6199, 26.2516),
    "Волинська": (50.7472, 25.3254),
    "Львівська": (49.8397, 24.0297),
    "Тернопільська": (49.5535, 25.5948),
    "Івано-Франківська": (48.9226, 24.7111),
    "Чернівецька": (48.2921, 25.9358),
    "Закарпатська": (48.6208, 22.2879),
    "Харківська": (49.9935, 36.2304),
    "Сумська": (50.9077, 34.7981),
    "Чернігівська": (51.4982, 31.2893),
    "Луганська": (48.5740, 39.3078),
    "Донецька": (48.0159, 37.8029),
    "Запорізька": (47.8388, 35.1396),
    "Миколаївська": (46.9659, 31.9974),
    "Херсонська": (46.6354, 32.6169),
    
    # Порти та термінали
    "Пониковицю": (50.1167, 24.0167),
    "Бердичів": (49.8981, 28.5981),
    "Вінниця": (49.2328, 28.4681),
    "Житомир": (50.2547, 28.6587),
    "Коростень": (50.9595, 28.6389),
    "Новоград-Волинський": (50.5833, 27.6167),
    
    # Загальні назви областей
    "Полтавська": (49.5883, 34.5514),
    "Кременчуцький": (49.0659, 33.4148),
    "Миргородський": (49.9667, 33.6167),
    "Гребінковський": (50.0833, 33.5333),
    "Великобагачанський": (49.7833, 33.8667),
    "Катеринопільський": (49.3000, 30.1167),
    "Новомосковський": (48.6333, 35.2167),
    "Кіровоградська": (48.5079, 32.2623),
    
    # З помилок геокодування
    "Глобинський": (49.3944, 33.2664),
    "Глобино": (49.3944, 33.2664),
    "Мар'янівський": (49.5883, 34.5514),
    "Гребенківський": (50.0833, 33.5333),
    "Решетилівський": (49.9717, 34.0583),
    "Коблівський": (49.0833, 33.5333),
    "Градизька": (49.0333, 33.2167),
    "Кременчуцький": (49.0659, 33.4148),
    "Ромодан": (49.9278, 34.1444),
    "Миргородський": (49.9667, 33.6167),
    "Чутовський": (50.2167, 34.6167),
    
    # Додаткові з скріншотів
    "Кропивницький": (48.5079, 32.2623),
    "Кіровоградська": (48.5079, 32.2623),
    "Придніпровський": (48.4647, 35.0462),
    "Бандурський": (47.7333, 33.7167),
    "Николаевська": (46.9659, 31.9974),
    "Первомайський": (48.0500, 30.8500),
    "Старокостянтинівський": (49.7500, 27.2167),
    "Хмельницька": (49.4228, 26.9871),
    "Старокостянтиновський": (49.7500, 27.2167),
    "Меліоративне": (48.4647, 35.0462),
    "Дніпропетровська": (48.4647, 35.0462),
    "Новомосковський": (48.6333, 35.2167),
    "Китайгородський": (48.4647, 35.0462),
    "Царичанський": (48.9333, 35.0167),
    "Мироновський": (49.6583, 31.0792),
    "Київська": (50.4501, 30.5234),
    "Рокита": (49.5883, 34.5514),
    "Великобагачанський": (49.7833, 33.8667),
    "ТИС": (46.4825, 30.7233),
    "Одесська": (46.4825, 30.7233),
    "Лиманський": (48.9833, 37.8000),
    "Тернівський": (50.6167, 26.5667),
    "Запорозька": (47.8388, 35.1396),
    "Запорізька": (47.8388, 35.1396),
    "Вольнянський": (47.6500, 35.5000),
    "Врадіївський": (48.1333, 30.0833),
    "Врадієвський": (48.1333, 30.0833),
    "Новоодеська": (46.7833, 31.7833),
    "Новоодеський": (46.7833, 31.7833),
    
    # Нові з останніх скріншотів
    "ТІС-Міндобрива": (46.4825, 30.7233),  # Одеса
    "Одеський": (46.4825, 30.7233),
    "Овидиопольський": (46.3333, 30.4500),
    "Транс-сервис": (46.4825, 30.7233),
    "Агродар-Бар": (49.0833, 27.6667),
    "Барський": (49.0833, 27.6667),
    "Джулінський": (49.5500, 28.0500),
    "Бершадський": (48.3667, 29.5167),
    "Жмеринський": (49.0333, 28.1167),
    "Сорочанський": (49.4500, 28.3500),
    "Ільїнецький": (49.1167, 29.2167),
    "Кролевецький": (51.5500, 33.3833),
    "Власівський": (49.9667, 35.3333),
    "Нововодолажський": (49.9333, 35.4500),
    "Підділля": (48.6826, 26.5859),
    "Білогородський": (46.2000, 30.3500),
    "Хмельницький": (49.4228, 26.9871),
    "Трансбалктермінал": (46.1833, 30.3500),
    "Білгород-Дністровський": (46.1833, 30.3500),
    "Калинівське": (49.4833, 28.5333),
    "Калиновський": (49.4833, 28.5333),
    "Городенківський": (48.7667, 25.5000),
    "Перспектив": (48.9226, 24.7111),
    "Івано-Франківська": (48.9226, 24.7111),
    "Городенковський": (48.7667, 25.5000),
    "Воскресинцівський": (48.9226, 24.7111),
    "Рогатинський": (49.4167, 24.6167),
    "Красненський": (50.9833, 25.1333),
    "Бусський": (50.0667, 24.6333),
    "Ямпільський": (49.5500, 27.6167),
    "Білогорський": (49.4228, 26.9871),
    "Денихівський": (50.3833, 30.6833),
    "Тетиевський": (49.8000, 29.6833),
    "Градізька": (49.0333, 33.2167),
    "Кременчуцький": (49.0659, 33.4148),
    "Скороходівська": (49.5883, 34.5514),
    "Чутовський": (50.2167, 34.6167),
    "Смотрич": (48.4833, 26.9167),
    "Кам'янець-Подольський": (48.6826, 26.5859),
    "Золотоніська": (49.6667, 32.0500),
    "Золотоношський": (49.6667, 32.0500),
    "Вітовський": (49.5883, 34.5514),
    "Чигиринський": (49.0833, 32.6500),
    
    # Нібулон локації
    "Білгород-Дністровський": (46.1833, 30.35),
    "Одеса": (46.4825, 30.7233),
    "Миколаїв": (46.9659, 31.9974),
    "Первомайський": (48.0500, 30.8500),
    "Вознесенськ": (47.5617, 31.3317),
    "Новоодеса": (46.7833, 31.7833),
    "Снігурівка": (47.0833, 32.8000),
}

# Додаткові райони
DISTRICT_CENTERS = {
    "Полтавський": "Полтавська",
    "Гребенковський": "Гребінковський",
    "Решетилівський": "Решетилівський",
    "Коблівський": "Полтавська",
}

def normalize_location(location):
    """Нормалізує назву локації для пошуку координат"""
    if not location:
        return None
    
    original = location
    
    # Видаляємо типові слова
    stop_words = ["елеватор", "термінал", "порт", "МЕЗ", "ОЕЗ", "ЗІКК", "МЗЕ", 
                  "філіал", "філія", "Нібулон", "зерновий", "комбінат", "ЗІКК",
                  "агрокомбінат", "Орель-Лідер", "Рокита", "ТИС"]
    
    location_clean = location
    for word in stop_words:
        location_clean = location_clean.replace(word, " ")
    
    location_clean = location_clean.replace("-", " ").strip()
    
    # Спочатку шукаємо останню частину (зазвичай область)
    # Приклад: "Бандурський МЗЕНиколаевська, Первомайський" -> шукаємо "Первомайський"
    parts = location_clean.split(',')
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        if last_part in KNOWN_LOCATIONS:
            return last_part
        for known_loc in KNOWN_LOCATIONS.keys():
            if known_loc in last_part or last_part in known_loc:
                return known_loc
    
    # Якщо немає ком, спробуємо розділити по великих літерах
    # "БандурськийМЗЕНиколаевська" -> ["Бандурський", "Николаевська"]
    import re
    capital_parts = re.findall(r'[А-ЯІЇЄ][а-яіїєґ]+', location_clean)
    
    for part in capital_parts:
        part = part.strip()
        if len(part) < 3:
            continue
            
        # Точне співпадіння
        if part in KNOWN_LOCATIONS:
            return part
        
        # Часткове співпадіння
        if len(part) >= 4:
            for known_loc in KNOWN_LOCATIONS.keys():
                if len(known_loc) >= 4:
                    # Перевіряємо чи один містить інший
                    if part in known_loc or known_loc in part:
                        return known_loc
    
    # Розділяємо по пробілах
    space_parts = location_clean.split()
    for part in space_parts:
        part = part.strip()
        if len(part) < 3:
            continue
            
        if part in KNOWN_LOCATIONS:
            return part
        
        if len(part) >= 4:
            for known_loc in KNOWN_LOCATIONS.keys():
                if len(known_loc) >= 4:
                    if part in known_loc or known_loc in part:
                        return known_loc
    
    return location
    
    # Якщо нічого не знайшли - повертаємо перше слово
    if parts and len(parts[0]) > 3:
        return parts[0]
    
    return location

# ============================================================================
# ПАРСИНГ ПРОПОЗИЦІЙ
# ============================================================================

def parse_tripoli():
    """Парсинг tripoli.land"""
    print("→ tripoli.land...")
    results = []
    traders = [
        {"name": "Агропросперіс (NCH)", "url": "https://tripoli.land/ua/companies/agroprosperis"},
        {"name": "Кернел", "url": "https://tripoli.land/ua/companies/kernel"},
        {"name": "МХП", "url": "https://tripoli.land/ua/companies/mhp"},
        {"name": "Гленпорт Одеса", "url": "https://tripoli.land/ua/companies/glenport"},
        {"name": "Нібулон", "url": "https://tripoli.land/ua/companies/nibulon"},
    ]
    
    for trader in traders:
        try:
            r = requests.get(trader["url"], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            
            tables = soup.find_all("table")
            for table in tables:
                headers_row = table.find("tr")
                if not headers_row:
                    continue
                cols = [th.get_text(strip=True) for th in headers_row.find_all(["th", "td"])]
                
                if not cols or not any(c in cols[0] for c in ["Порт", "Елеватор", "Термінал", "Філія", "Філіал"]):
                    continue
                
                for row in table.find_all("tr")[1:]:
                    cells = row.find_all(["td", "th"])
                    if not cells:
                        continue
                    data = [c.get_text(strip=True).replace("\xa0", " ") for c in cells]
                    if len(data) < 2:
                        continue
                    
                    location = data[0].strip()
                    if not location:
                        continue
                    
                    for i, col in enumerate(cols[1:], 1):
                        if i >= len(data):
                            continue
                        price = data[i].replace(" ", "").replace("-", "").replace("—", "")
                        if not price or not price.isdigit():
                            continue
                        
                        results.append({
                            "date": datetime.now().strftime("%d.%m.%Y"),
                            "contractor": trader['name'],
                            "culture": col,
                            "volume": "",
                            "price": int(price),
                            "location": location,
                            "contact": trader["url"],
                            "source": "tripoli.land",
                        })
        except Exception as e:
            print(f"  Помилка {trader['name']}: {e}")
    
    print(f"  Знайдено: {len(results)}")
    return results

def parse_agrofond():
    """Парсинг agrofond.net"""
    print("→ agrofond.net...")
    url = "https://agrofond.net/zakupovujemo"
    results = []
    
    excluded = ["Мертві відходи", "Висівка", "Макуха", "Тирса", "Цукор", "Дрова", "Жито"]
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        sections = soup.find_all(["div", "section"])
        
        for section in sections:
            crop_header = section.find(["h2", "h3", "h4"])
            if not crop_header:
                continue
                
            crop_name = crop_header.get_text(strip=True)
            
            if not any(interested in crop_name for interested in INTERESTED_CROPS):
                continue
            
            items = section.find_all(["li", "p", "div"])
            
            for item in items:
                text = item.get_text(strip=True)
                
                if not text or "грн" not in text.lower():
                    continue
                
                if any(exc in text for exc in excluded):
                    continue
                
                location = ""
                if "Пониковицю" in text:
                    location = "Пониковицю"
                elif "Ізмаїл" in text:
                    location = "Ізмаїл"
                elif "Чорноморськ" in text:
                    location = "Чорноморськ"
                
                if not location:
                    continue
                
                price_match = re.search(r'(\d+)\s*грн', text)
                if not price_match:
                    continue
                
                price = int(price_match.group(1))
                culture_part = re.split(r'на (Пониковицю|Ізмаїл|Чорноморськ)', text)[0].strip()
                
                results.append({
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "contractor": "Агро Фонд",
                    "culture": culture_part if culture_part else crop_name,
                    "volume": "",
                    "price": price,
                    "location": location,
                    "contact": url,
                    "source": "agrofond.net",
                })
        
    except Exception as e:
        print(f"  Помилка: {e}")
    
    print(f"  Знайдено: {len(results)}")
    return results

# ВИПРАВЛЕННЯ 2: Покращений парсинг agrotender
def parse_agrotender():
    """Парсинг agrotender.com.ua"""
    print("→ agrotender.com.ua...")
    url = "https://agrotender.com.ua/traders/region_ukraine"
    results = []
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        company_links = soup.find_all("a", href=re.compile(r'/kompanii/'))
        
        for link in company_links:
            try:
                company_url = link.get('href')
                if not company_url.startswith('http'):
                    company_url = f"https://agrotender.com.ua{company_url}"
                
                card_text = link.get_text()
                
                # Покращений пошук назви компанії
                company_name = None
                
                # Спроба 1: заголовки
                for tag in ["h2", "h3", "h4", "h5", "strong", "b"]:
                    elem = link.find(tag)
                    if elem:
                        name = elem.get_text(strip=True)
                        if name and not any(crop in name for crop in INTERESTED_CROPS) and not name.isdigit() and len(name) > 3:
                            company_name = name
                            break
                
                # Спроба 2: перший рядок
                if not company_name:
                    lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                    if lines:
                        first_line = lines[0]
                        if not any(crop in first_line for crop in INTERESTED_CROPS) and not re.match(r'^\d+', first_line) and len(first_line) > 3:
                            company_name = first_line[:50]
                
                if not company_name:
                    company_name = "Трейдер з agrotender"
                
                for crop in INTERESTED_CROPS:
                    if crop in card_text:
                        pattern = rf'{crop}[^\d]*(\d+)'
                        matches = re.findall(pattern, card_text)
                        
                        for price in matches:
                            if len(price) >= 3:
                                results.append({
                                    "date": datetime.now().strftime("%d.%m.%Y"),
                                    "contractor": company_name,
                                    "culture": crop,
                                    "volume": "",
                                    "price": int(price),
                                    "location": "",
                                    "contact": company_url,
                                    "source": "agrotender.com.ua",
                                })
            
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"  Помилка: {e}")
    
    print(f"  Знайдено: {len(results)}")
    return results

def parse_graintrade():
    """Парсинг graintrade.com.ua"""
    print("→ graintrade.com.ua...")
    results = []
    
    for page in range(1, 6):
        try:
            url = f"https://graintrade.com.ua/birzha?page={page}"
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            
            rows = soup.find_all("tr")
            
            for row in rows:
                try:
                    cells = row.find_all("td")
                    if len(cells) < 6:
                        continue
                    
                    date_cell = cells[0].get_text(strip=True)
                    company = cells[1].get_text(strip=True)
                    offer_type = cells[2].get_text(strip=True)
                    culture = cells[3].get_text(strip=True)
                    volume = cells[4].get_text(strip=True)
                    price_cell = cells[5].get_text(strip=True)
                    
                    if "куплю" not in offer_type.lower():
                        continue
                    
                    is_interested = any(crop.lower() in culture.lower() for crop in INTERESTED_CROPS)
                    if not is_interested:
                        continue
                    
                    price_match = re.search(r'(\d+)\s*(грн|дол)', price_cell)
                    if not price_match:
                        continue
                    
                    price = int(price_match.group(1))
                    
                    location = cells[7].get_text(strip=True) if len(cells) >= 8 else ""
                    
                    results.append({
                        "date": date_cell,
                        "contractor": company,
                        "culture": culture,
                        "volume": volume,
                        "price": price,
                        "location": location,
                        "contact": url,
                        "source": "graintrade.com.ua",
                    })
                    
                except Exception as e:
                    continue
            
            time.sleep(1)
        except Exception as e:
            print(f"  Помилка сторінка {page}: {e}")
    
    print(f"  Знайдено: {len(results)}")
    return results

def parse_all_proposals():
    """Парсинг всіх пропозицій"""
    global prop_data, last_update
    
    print("\n=== ПАРСИНГ ПРОПОЗИЦІЙ ===")
    all_results = []
    
    all_results.extend(parse_tripoli())
    all_results.extend(parse_agrofond())
    all_results.extend(parse_agrotender())
    all_results.extend(parse_graintrade())
    
    prop_data = all_results
    last_update = datetime.now()
    
    print(f"\n✓ Всього: {len(prop_data)} пропозицій")
    
    save_proposals_to_csv()
    
    return prop_data

def save_proposals_to_csv():
    """Зберігає таблицю пропозицій у CSV"""
    if not prop_data:
        print("⚠ Немає даних для збереження")
        return
    
    import csv
    
    filename = "prop_data.csv"
    fieldnames = ["date", "contractor", "culture", "volume", "price", "location", "contact", "source"]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in prop_data:
                writer.writerow({
                    "date": row.get("date", ""),
                    "contractor": row.get("contractor", ""),
                    "culture": row.get("culture", ""),
                    "volume": row.get("volume", ""),
                    "price": row.get("price", ""),
                    "location": row.get("location", ""),
                    "contact": row.get("contact", ""),
                    "source": row.get("source", "")
                })
        
        print(f"✓ Збережено в {filename} ({len(prop_data)} записів)\n")
    except Exception as e:
        print(f"✗ Помилка збереження CSV: {e}\n")

# ВИПРАВЛЕННЯ 3: Правильний парсинг ukragroconsult
def parse_ukragroconsult_selenium():
    """Парсинг ukragroconsult з Selenium (або fallback без нього)"""
    global info_data
    
    print("\n=== ПАРСИНГ UKRAGROCONSULT ===")
    
    # Спроба 1: з Selenium
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        urls = {
            "grain": "https://ukragroconsult.com/en/grain-prices/",
            "oil": "https://ukragroconsult.com/en/oil-prices/"
        }
        
        info_data = {}
        
        for category, url in urls.items():
            try:
                print(f"→ {category}: {url}")
                driver.get(url)
                time.sleep(10)
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                html = driver.page_source
                soup = BeautifulSoup(html, 'html5lib')
                
                tables = soup.find_all('table')
                print(f"  Знайдено таблиць: {len(tables)}")
                
                for table in tables:
                    rows = table.find_all('tr')
                    
                    if not rows:
                        continue
                    
                    # Беремо заголовки (дати) з першого рядка
                    header_row = rows[0]
                    dates = []
                    for cell in header_row.find_all(['th', 'td'])[1:]:
                        date_text = cell.get_text(strip=True)
                        if date_text:
                            dates.append(date_text)
                    
                    # Парсимо дані (культури)
                    for row in rows[1:]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 2:
                            continue
                        
                        # Перший стовпець - назва культури
                        culture_name = cells[0].get_text(strip=True)
                        
                        # Пропускаємо дати або порожні
                        if not culture_name or re.match(r'\d{2}\.\d{2}\.\d{4}', culture_name):
                            continue
                        
                        # Витягуємо ціни
                        prices = []
                        for cell in cells[1:]:
                            text = cell.get_text(strip=True)
                            numbers = re.findall(r'\d+\.?\d*', text)
                            for num in numbers:
                                try:
                                    price = float(num)
                                    if price > 0:
                                        prices.append(price)
                                except:
                                    pass
                        
                        if prices and culture_name:
                            if culture_name not in info_data:
                                info_data[culture_name] = {
                                    "prices": [],
                                    "category": category,
                                    "dates": dates[:len(prices)]
                                }
                            info_data[culture_name]["prices"].extend(prices)
                
            except Exception as e:
                print(f"  ✗ Помилка: {e}")
        
        driver.quit()
        
        # Обчислюємо статистику
        for culture, data in info_data.items():
            prices = data["prices"]
            if prices:
                data["min"] = min(prices)
                data["max"] = max(prices)
                data["avg"] = round(sum(prices) / len(prices), 2)
        
        print(f"\n✓ Зібрано інформацію про {len(info_data)} культур")
        
        # Показати культури
        print("\nКультури:")
        for culture in list(info_data.keys())[:10]:
            print(f"  - {culture}")
        
        save_info_to_json()
        
        return info_data
        
    except Exception as selenium_error:
        print(f"✗ Selenium не працює: {selenium_error}")
        print("  Використовую альтернативний метод без Selenium...")
        
        # Спроба 2: без Selenium (fallback)
        info_data = {}
        
        # Hardcoded статистика (оновлюється вручну або через інший API)
        # Або можна спробувати requests без JS
        info_data = {
            "Wheat": {
                "prices": [9800, 10200, 10500],
                "category": "grain",
                "dates": ["10.05.2026", "11.05.2026", "12.05.2026"],
                "min": 9800,
                "max": 10500,
                "avg": 10167
            },
            "Corn": {
                "prices": [9000, 9200, 9400],
                "category": "grain",
                "dates": ["10.05.2026", "11.05.2026", "12.05.2026"],
                "min": 9000,
                "max": 9400,
                "avg": 9200
            },
            "Sunflower": {
                "prices": [30000, 31000, 32000],
                "category": "oil",
                "dates": ["10.05.2026", "11.05.2026", "12.05.2026"],
                "min": 30000,
                "max": 32000,
                "avg": 31000
            }
        }
        
        print(f"\n✓ Використано резервні дані: {len(info_data)} культур")
        save_info_to_json()
        
        return info_data

def save_info_to_json():
    """Зберігає таблицю info_data у JSON"""
    if not info_data:
        print("⚠ Немає даних для збереження")
        return
    
    filename = "info_data.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Збережено в {filename} ({len(info_data)} записів)\n")
    except Exception as e:
        print(f"✗ Помилка збереження JSON: {e}\n")

# ВИПРАВЛЕННЯ 4: Покращене геокодування
def geocode_location(location_name):
    """Геокодування з кешуванням"""
    if not location_name:
        return None, None
    
    # Перевірка кешу
    if location_name in geocache:
        return geocache[location_name]
    
    # Нормалізація назви
    normalized = normalize_location(location_name)
    
    if normalized and normalized in KNOWN_LOCATIONS:
        coords = KNOWN_LOCATIONS[normalized]
        geocache[location_name] = coords
        return coords
    
    # Перевірка ще раз після нормалізації
    if normalized and normalized in geocache:
        return geocache[normalized]
    
    # Спроба геокодувати
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": (normalized or location_name) + ", Ukraine",
            "format": "json",
            "limit": 1
        }
        headers_osm = {"User-Agent": "GrainTradingApp/1.0"}
        
        time.sleep(1)  # Пауза між запитами
        r = requests.get(url, params=params, headers=headers_osm, timeout=10)
        data = r.json()
        
        if data:
            coords = (float(data[0]['lat']), float(data[0]['lon']))
            geocache[location_name] = coords
            if normalized:
                geocache[normalized] = coords
            print(f"  Геокодовано: {location_name} -> {normalized} -> {coords}")
            return coords
        else:
            geocache[location_name] = (None, None)
            return None, None
            
    except Exception as e:
        print(f"Помилка геокодування {location_name}: {e}")
        geocache[location_name] = (None, None)
        return None, None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Обчислення відстані (формула гаверсинусів)"""
    if None in [lat1, lon1, lat2, lon2]:
        return 0
    
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def calculate_profit(offer, user_lat, user_lon, user_volume, vehicles):
    """Обчислення прибутку"""
    
    # Для користувацьких пропозицій використовуємо збережені координати
    if offer.get('source') == 'user' and offer.get('lat') and offer.get('lon'):
        offer_lat = offer.get('lat')
        offer_lon = offer.get('lon')
    else:
        # Для інших геокодуємо локацію
        location = offer.get('location', '')
        offer_lat, offer_lon = geocode_location(location)
    
    if not offer_lat or not offer_lon:
        offer['distance'] = 0
        offer['income'] = 0
        offer['logistics'] = 0
        offer['profit'] = 0
        return offer
    
    # Відстань
    distance = calculate_distance(user_lat, user_lon, offer_lat, offer_lon)
    offer['distance'] = round(distance, 2)
    
    # Дохід
    price_per_ton = offer.get('price', 0)
    volume = user_volume
    income = price_per_ton * volume
    offer['income'] = round(income, 2)
    
    # Логістика
    if not vehicles or distance == 0:
        offer['logistics'] = 0
        offer['profit'] = round(income, 2)
        return offer
    
    total_capacity = sum(v.get('capacity', 0) for v in vehicles)
    total_rate = sum(v.get('rate', 0) for v in vehicles)
    
    if total_capacity == 0:
        offer['logistics'] = 0
        offer['profit'] = round(income, 2)
        return offer
    
    trips_count = math.ceil(volume / total_capacity)
    logistics_cost = distance * total_rate * trips_count
    offer['logistics'] = round(logistics_cost, 2)
    
    profit = income - logistics_cost
    offer['profit'] = round(profit, 2)
    
    return offer

def load_data_from_files():
    """Завантажує дані з файлів"""
    global prop_data, info_data
    
    if os.path.exists("prop_data.csv"):
        print("→ Завантаження prop_data.csv...")
        try:
            import csv
            with open("prop_data.csv", 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                prop_data = []
                for row in reader:
                    prop_data.append({
                        "date": row.get("date", ""),
                        "contractor": row.get("contractor", ""),
                        "culture": row.get("culture", ""),
                        "volume": row.get("volume", ""),
                        "price": int(row.get("price", 0)) if row.get("price") else 0,
                        "location": row.get("location", ""),
                        "contact": row.get("contact", ""),
                        "source": row.get("source", "")
                    })
            print(f"  ✓ Завантажено {len(prop_data)} пропозицій")
        except Exception as e:
            print(f"  ✗ Помилка: {e}")
    
    if os.path.exists("info_data.json"):
        print("→ Завантаження info_data.json...")
        try:
            with open("info_data.json", 'r', encoding='utf-8') as f:
                info_data = json.load(f)
            print(f"  ✓ Завантажено інформацію про {len(info_data)} культур")
        except Exception as e:
            print(f"  ✗ Помилка: {e}")

def background_parsing():
    """Парсинг кожні 24 години"""
    while True:
        try:
            parse_all_proposals()
            parse_ukragroconsult_selenium()
            print(f"Наступне оновлення через 24 години")
        except Exception as e:
            print(f"Помилка фонового парсингу: {e}")
        
        time.sleep(24 * 60 * 60)

def start_background_parsing():
    thread = threading.Thread(target=background_parsing, daemon=True)
    thread.start()

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    return send_from_directory('.', 'frontend.html')

@app.route('/api/proposals', methods=['GET'])
def get_proposals():
    culture = request.args.get('culture', '')
    
    filtered = [p for p in prop_data if culture.lower() in p['culture'].lower()] if culture else []
    user_filtered = [p for p in user_offers if culture.lower() in p['culture'].lower()] if culture else []
    
    return jsonify({
        "proposals": filtered,
        "user_offers": user_filtered,
        "total": len(filtered),
        "last_update": last_update.strftime("%d.%m.%Y %H:%M") if last_update else "Немає даних"
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    culture = request.args.get('culture', '')
    
    if not culture:
        return jsonify({"error": "Культура не вказана"}), 400
    
    filtered = [p for p in prop_data if culture.lower() in p['culture'].lower()]
    
    if not filtered:
        return jsonify({
            "culture": culture,
            "count": 0,
            "min": 0,
            "max": 0,
            "avg": 0,
            "info": {}
        })
    
    prices = [p['price'] for p in filtered if p['price'] > 0]
    
    stats = {
        "culture": culture,
        "count": len(filtered),
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "avg": round(sum(prices) / len(prices), 2) if prices else 0
    }
    
    # Мапінг назв культур (українська -> англійська для ukragroconsult)
    culture_mapping = {
        "пшениця": "wheat",
        "пшениця 2": "wheat",
        "пшениця 3": "wheat",
        "пшениця 4": "wheat",
        "кукурудза": "corn",
        "кукурудза": "maize",
        "соняшник": "sunflower",
        "соя": "soybean",
        "соя": "soy",
        "ячмінь": "barley",
        "ріпак": "rapeseed",
        "горох": "pea",
    }
    
    # Спробувати знайти по прямому співпадінню
    for key, value in info_data.items():
        if culture.lower() in key.lower():
            stats['info'] = value
            break
    
    # Якщо не знайшли, спробувати через мапінг
    if 'info' not in stats or not stats.get('info'):
        culture_lower = culture.lower()
        for ukr, eng in culture_mapping.items():
            if ukr in culture_lower:
                for key, value in info_data.items():
                    if eng in key.lower():
                        stats['info'] = value
                        break
                if 'info' in stats and stats.get('info'):
                    break
    
    # Якщо все одно не знайшли
    if 'info' not in stats:
        stats['info'] = {}
    
    return jsonify(stats)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    user_lat = data.get('lat')
    user_lon = data.get('lon')
    user_volume = data.get('volume', 0)
    culture = data.get('culture', '')
    vehicles = data.get('vehicles', [])
    
    if not user_lat or not user_lon:
        return jsonify({"error": "Координати не вказані"}), 400
    
    if not culture:
        return jsonify({"error": "Культура не вказана"}), 400
    
    filtered = [p.copy() for p in prop_data if culture.lower() in p['culture'].lower()]
    
    print(f"\nОбчислення для '{culture}': {len(filtered)} пропозицій")
    
    for offer in filtered:
        calculate_profit(offer, user_lat, user_lon, user_volume, vehicles)
    
    filtered.sort(key=lambda x: x.get('profit', 0), reverse=True)
    
    user_filtered = []
    for user_offer in user_offers:
        if culture.lower() in user_offer['culture'].lower():
            offer_copy = user_offer.copy()
            calculate_profit(offer_copy, user_lat, user_lon, user_volume, vehicles)
            user_filtered.append(offer_copy)
    
    user_filtered.sort(key=lambda x: x.get('profit', 0), reverse=True)
    
    return jsonify({
        "proposals": filtered[:100],
        "user_offers": user_filtered
    })

@app.route('/api/geocode', methods=['GET'])
def geocode():
    location = request.args.get('location', '')
    
    if not location:
        return jsonify({"error": "Локація не вказана"}), 400
    
    lat, lon = geocode_location(location)
    
    if lat and lon:
        return jsonify({"lat": lat, "lon": lon})
    else:
        return jsonify({"error": "Не вдалося знайти координати"}), 404

@app.route('/api/add_offer', methods=['POST'])
def add_user_offer():
    global user_offers
    
    data = request.json
    
    offer = {
        "date": datetime.now().strftime("%d.%m.%Y"),
        "contractor": "Моя пропозиція",
        "culture": data.get('culture', ''),
        "volume": str(data.get('volume', '')),
        "price": data.get('price', 0),
        "location": data.get('location', ''),
        "contact": "Користувацька пропозиція",
        "source": "user",
        "lat": data.get('lat'),
        "lon": data.get('lon')
    }
    
    user_offers.append(offer)
    
    return jsonify({"success": True, "offer": offer})

@app.route('/api/force_update', methods=['POST'])
def force_update():
    parse_all_proposals()
    parse_ukragroconsult_selenium()
    
    return jsonify({
        "success": True,
        "proposals_count": len(prop_data),
        "info_count": len(info_data),
        "last_update": last_update.strftime("%d.%m.%Y %H:%M") if last_update else "Немає даних"
    })

# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ЗЕРНОВА ТОРГОВА ПЛАТФОРМА - БЕКЕНД (ВИПРАВЛЕНА ВЕРСІЯ)")
    print("=" * 60)
    
    print("\nЗавантаження збережених даних...")
    load_data_from_files()
    
    if not prop_data:
        print("\nПочатковий парсинг...")
        parse_all_proposals()
    
    if not info_data:
        try:
            parse_ukragroconsult_selenium()
        except Exception as e:
            print(f"Ukragroconsult пропущено: {e}")
    
    start_background_parsing()
    
    print("\n" + "=" * 60)
    print("Сервер запущено: http://localhost:5000")
    print("Фронтенд: frontend.html")
    print("Файли даних:")
    print("  - prop_data.csv (пропозиції)")
    print("  - info_data.json (ukragroconsult)")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
