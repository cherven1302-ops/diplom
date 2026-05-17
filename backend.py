#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бекенд для зернової торгової платформи
Flask API + парсинг даних + OSM геокодування та розрахунок відстаней
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

app = Flask(__name__, static_folder='.')
CORS(app)

usd_rate = 41.0

def get_usd_rate():
    """Отримує курс USD/UAH з API ПриватБанку"""
    global usd_rate
    
    url = "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=11"
    try:
        res = requests.get(url, timeout=5).json()
        for currency in res:
            if currency['ccy'] == 'USD':
                rate = float(currency['sale'])
                usd_rate = rate
                print(f"Курс USD: {rate} грн")
                return rate
    except Exception as e:
        print(f"Помилка отримання курсу: {e}, використовую {usd_rate}")
    
    return usd_rate

get_usd_rate()

prop_data = []
info_data = {}
last_update = None
user_offers = []
geocache = {}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
INTERESTED_CROPS = ["Кукурудза", "Пшениця", "Соя", "Ячмінь", "Ріпак", "Горох", "Овес", "Гречка", "Цукровий буряк", "Соняшник"]

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
    
    "Сорочанський": (49.4500, 28.3500),
    "Ільїнецький": (49.1167, 29.2167),
    "Кролевецький": (51.5500, 33.3833),
    "Власівський": (49.9667, 35.3333),
    "Нововодолажський": (49.9333, 35.4500),
    "Підділля": (48.6826, 26.5859),
    "Білогородський": (46.2000, 30.3500),
    "Трансбалктермінал": (46.1833, 30.3500),
    "Білгород-Дністровський": (46.1833, 30.3500),
    "Калинівське": (49.4833, 28.5333),
    "Калиновський": (49.4833, 28.5333),
    "Городенківський": (48.7667, 25.5000),
    "Перспектив": (48.9226, 24.7111),
    "Городенковський": (48.7667, 25.5000),
    "Воскресинцівський": (48.9226, 24.7111),
    "Рогатинський": (49.4167, 24.6167),
    "Красненський": (50.9833, 25.1333),
    "Бусський": (50.0667, 24.6333),
    "Ямпільський": (49.5500, 27.6167),
    "Білогорський": (49.4228, 26.9871),
    "Денихівський": (50.3833, 30.6833),
    "Тетиевський": (49.8000, 29.6833),
    "Ізмаїльський": (45.3500, 28.8400),
    "Ягодин": (51.3833, 24.3167),
    "Іззів": (50.1333, 24.1500),
    "Александра": (46.4825, 30.7233),
    "Барський": (49.0833, 27.6667),
    "Агродар-Бар": (49.0833, 27.6667),
    "Бершадський": (48.3667, 29.5167),
    "Джулінський": (49.5500, 28.0500),
    "Жмеринський": (49.0333, 28.1167),
    "Конотопський": (51.2404, 33.2008),
    "Сумська": (50.9077, 34.7981),
    "Коблівський": (49.0833, 33.5333),
    "Решетилівський": (49.9717, 34.0583),
    "Великобагачанський": (49.7833, 33.8667),
    "Гребенківський": (50.0833, 33.5333),
    "Гребінковський": (50.0833, 33.5333),
    "Романівський": (49.5883, 34.5514),
    "Мар'янівський": (49.5883, 34.5514),
    "Градизька": (49.0333, 33.2167),
    "Градізька": (49.0333, 33.2167),
    "Ромодан": (49.9278, 34.1444),
    "Чутовський": (50.2167, 34.6167),
    "Скороходівська": (49.5883, 34.5514),
    "Вітовський": (49.5883, 34.5514),
    "Чигиринський": (49.0833, 32.6500),
    "Рокита": (49.5883, 34.5514),
    "Золотоніська": (49.6667, 32.0500),
    "Золотоношський": (49.6667, 32.0500),
    "Смотрич": (48.4833, 26.9167),
    "Кам'янець-Подольський": (48.6826, 26.5859),
    "Катеринопільський": (49.3000, 30.1167),
    "Мироновський": (49.6583, 31.0792),
    "Миронівський": (49.6583, 31.0792),
    "Врадіївський": (48.1333, 30.0833),
    "Врадієвський": (48.1333, 30.0833),
    "Новоодеська": (46.7833, 31.7833),
    "Новоодеський": (46.7833, 31.7833),
    "Бандурський": (47.7333, 33.7167),
    "Николаевська": (46.9659, 31.9974),
    "Первомайський": (48.0500, 30.8500),
    "Старокостянтинівський": (49.7500, 27.2167),
    "Старокостянтиновський": (49.7500, 27.2167),
    "Меліоративне": (48.4647, 35.0462),
    "Новомосковський": (48.6333, 35.2167),
    "Китайгородський": (48.4647, 35.0462),
    "Царичанський": (48.9333, 35.0167),
    "Придніпровський": (48.4647, 35.0462),
    "Лиманський": (48.9833, 37.8000),
    "Тернівський": (50.6167, 26.5667),
    "Вольнянський": (47.6500, 35.5000),
    "ТІС-Міндобрива": (46.4825, 30.7233),
    "ТИС-Міндобрива": (46.4825, 30.7233),
    "Одеський": (46.4825, 30.7233),
    "Овидиопольський": (46.3333, 30.4500),
    "Транс-сервис": (46.4825, 30.7233),
    "Транс-сервіс": (46.4825, 30.7233),
    "Лиманський": (46.4825, 30.7233),
    "Овидіопольський": (46.3333, 30.4500),
    "Бердичів": (49.8981, 28.5981),
    "Коростень": (50.9595, 28.6389),
    "Новоград-Волинський": (50.5833, 27.6167),
    "Кременчуцький": (49.0659, 33.4148),
    "Миргородський": (49.9667, 33.6167),
    "Гребінковський": (50.0833, 33.5333),
    "Пониковицю": (50.1167, 24.0167),
    "Пониковицю": (50.1167, 24.0167),
    
    "Кропивницький": (48.5079, 32.2623),
    "Придніпровський": (48.4647, 35.0462),
    "Бандурський": (47.7333, 33.7167),
    "Полтавський": (49.5883, 34.5514),
    "Глобинський": (49.3944, 33.2664),
    "Хорольський": (49.5167, 33.2667),
    "Тетиєвський": (49.8000, 29.6833),
    "Київська": (50.4501, 30.5234),
    "Вознесенська": (47.5617, 31.3317),
    "Вознесенський": (47.5617, 31.3317),
    "Глобинський": (49.3944, 33.2664),
    "Хмільницький": (49.5667, 27.9667),
    "Тульчинський": (48.6753, 28.8514),
    "Шликовський": (49.4228, 26.9871),
    "Лодзь": (51.7592, 19.4560),
    "Польща": (52.2297, 21.0122),
    "Білоцерківський": (49.7880, 30.1119),
    "Білопродукт": (49.7880, 30.1119),
    "Білоцерківка": (49.7880, 30.1119),
    "Велико-Багачанський": (49.7833, 33.8667),
    "Чорноморськ": (46.3061, 30.6561),
    "Чорноморський": (46.3061, 30.6561),
    "Миргород": (49.9667, 33.6167),
    "Миргородський": (49.9667, 33.6167),
    "Краснопавлівка": (49.9935, 36.2304),
    "Прилуки": (50.5950, 32.3897),
    "Прилуцький": (50.5950, 32.3897),
    "Марганець": (47.6406, 34.6211),
    "Маргаганець": (47.6406, 34.6211),
    "Власівка": (49.7880, 30.1119),
    "Чорнобай": (49.2167, 32.4833),
    "Чорнобаївський": (49.2167, 32.4833),
    "Брукін-Київ": (50.4501, 30.5234),
    "Південний МП": (46.4825, 30.7233),
    "Одеський МП": (46.4825, 30.7233),
    "Устилуг": (50.9833, 24.3000),
    "Київська обл.м.Київ": (50.4501, 30.5234),
    "Волинська обл.Устилуг": (50.9833, 24.3000),
    "Вінниця": (49.2328, 28.4681),
    "Бердичівський": (49.8981, 28.5981),
    "Андрушівський": (50.0167, 28.8667),
    "Б. Церква": (49.7880, 30.1119),
    "Бориспільський": (50.3900, 30.9550),
    "Броварський": (50.5108, 30.7928),
    "Васильків": (50.1833, 30.3167),
    "Переяслав": (50.0667, 31.4500),
    "Суми": (50.9077, 34.7981),
    "Черкаси": (49.4285, 32.0624),
    "Чернігів": (51.4982, 31.2893),
    "Броди": (50.0833, 25.1500),
    "Полтавська обл.Миргород": (49.9667, 33.6167),
    "Чернігівська обл.Прилуки": (50.5950, 32.3897),
    "Харківська обл.Краснопавлівка": (49.9935, 36.2304),
    "Київська обл.Б. Церква": (49.7880, 30.1119),
    "Київська обл.Васильків": (50.1833, 30.3167),
    "Вінницька обл.Вінниця": (49.2328, 28.4681),
    "Житомирська обл.ТОВ Андрушівський елеватор": (50.0167, 28.8667),
    "Львівська обл.Броди": (50.0833, 25.1500),
}


def get_coordinates_osm(address):
    """
    Шукає координати (lat, lon) за текстовою назвою локації через OpenStreetMap
    Повертає: (lat, lon, display_name) або None
    """
    url = "https://nominatim.openstreetmap.org/search"
    osm_headers = {
        'User-Agent': 'MyAgroDistanceApp/1.0 (cherven1302@gmail.com)'
    }
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    
    try:
        response = requests.get(url, headers=osm_headers, params=params, timeout=5).json()
        if response:
            lat = float(response[0]['lat'])
            lon = float(response[0]['lon'])
            display_name = response[0].get('display_name', address)
            # Повертаємо координати та коротку назву
            short_name = ", ".join(display_name.split(",")[:2])
            print(f"  ✓ OSM знайшов '{address}': {lat}, {lon}")
            return lat, lon, short_name
    except Exception as e:
        print(f"  ✗ OSM не знайшов '{address}': {e}")
    
    return None


def get_road_distance_osrm(lat1, lon1, lat2, lon2):
    """
    Рахує реальну відстань та час між двома координатами по дорогах через OSRM
    Повертає: (distance_km, duration_min) або None
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    
    try:
        response = requests.get(url, timeout=10).json()
        if response['code'] == 'Ok':
            route = response['routes'][0]
            distance_km = route['distance'] / 1000  # Переводимо метри в км
            duration_min = route['duration'] / 60   # Переводимо секунди в хвилини
            print(f"  ✓ OSRM розрахував відстань: {distance_km:.2f} км, {duration_min:.0f} хв")
            return distance_km, duration_min
    except Exception as e:
        print(f"  ✗ OSRM помилка: {e}")
    
    return None


def geocode_location(location):
    """
    Визначає координати локації з пріоритетом OSM
    1. Спочатку пробує OSM
    2. Якщо не вдалося, шукає в KNOWN_LOCATIONS з нормалізацією
    Повертає: (lat, lon) або (None, None)
    """
    if not location:
        return None, None
    
    if location in geocache:
        return geocache[location]
    
    print(f"\nГеокодування '{location}'...")
    
    osm_result = get_coordinates_osm(location)
    if osm_result:
        lat, lon, _ = osm_result
        geocache[location] = (lat, lon)
        return lat, lon
    
    normalized = normalize_location(location)
    
    if normalized and normalized in KNOWN_LOCATIONS:
        coords = KNOWN_LOCATIONS[normalized]
        geocache[location] = coords
        print(f"  Знайдено в словнику: {normalized}")
        return coords
    
    if normalized and normalized in geocache:
        return geocache[normalized]
    
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": (normalized or location) + ", Ukraine",
            "format": "json",
            "limit": 1
        }
        headers_osm = {"User-Agent": "GrainTradingApp/1.0"}
        
        time.sleep(1)
        r = requests.get(url, params=params, headers=headers_osm, timeout=10)
        data = r.json()
        
        if data:
            coords = (float(data[0]['lat']), float(data[0]['lon']))
            geocache[location] = coords
            if normalized:
                geocache[normalized] = coords
            print(f"  Геокодовано через OSM: {location} -> {coords}")
            return coords
        else:
            geocache[location] = (None, None)
            return None, None
            
    except Exception as e:
        print(f"  Помилка геокодування {location}: {e}")
        geocache[location] = (None, None)
        return None, None


def haversine(lat1, lon1, lat2, lon2):
    """
    Розрахунок відстані по прямій (формула гаверсинусів)
    Використовується тільки як резервний варіант
    """
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def normalize_location(location):
    """Нормалізує назву локації для пошуку координат"""
    if not location:
        return None
    
    original = location
    
    stop_words = ["елеватор", "термінал", "порт", "МЕЗ", "ОЕЗ", "ЗІКК", "МЗЕ", 
                  "філіал", "філія", "Нібулон", "зерновий", "комбінат", "ЗІКК",
                  "агрокомбінат", "Орель-Лідер", "Рокита", "ТИС"]
    
    location_clean = location
    for word in stop_words:
        location_clean = location_clean.replace(word, " ")
    
    location_clean = location_clean.replace("-", " ").strip()
    
    parts = location_clean.split(',')
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        if last_part in KNOWN_LOCATIONS:
            return last_part
        for known_loc in KNOWN_LOCATIONS.keys():
            if known_loc in last_part or last_part in known_loc:
                return known_loc
    
    capital_parts = re.findall(r'[А-ЯІЇЄ][а-яіїєґ]+', location_clean)
    
    for part in capital_parts:
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


def parse_tripoli():
    """Парсинг tripoli.land"""
    print("Парсинг tripoli.land...")
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
                        price_text = data[i].replace(" ", "").replace("-", "").replace("—", "")
                        if not price_text or not price_text.isdigit():
                            continue
                        
                        price = int(price_text)
                        
                        currency = "грн"
                        if price < 1000:
                            currency = "дол"
                        
                        results.append({
                            "date": datetime.now().strftime("%d.%m.%Y"),
                            "contractor": trader['name'],
                            "culture": col,
                            "volume": "",
                            "price": price,
                            "currency": currency,
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
    print("Парсинг agrofond.net...")
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
                    "currency": "грн",
                    "location": location,
                    "contact": url,
                    "source": "agrofond.net",
                })
        
    except Exception as e:
        print(f"  Помилка: {e}")
    
    print(f"  Знайдено: {len(results)}")
    return results


def parse_agrotender():
    """Парсинг agrotender.com.ua"""
    print("Парсинг agrotender.com.ua...")
    url = "https://agrotender.com.ua/traders/region_ukraine"
    results = []
    
    months_uk = {
        'Січня': 1, 'Лютого': 2, 'Березня': 3, 'Квітня': 4, 'Травня': 5, 'Червня': 6,
        'Липня': 7, 'Серпня': 8, 'Вересня': 9, 'Жовтня': 10, 'Листопада': 11, 'Грудня': 12
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        company_links = soup.find_all("a", href=re.compile(r'/kompanii/'))
        
        processed_urls = set()
        
        for link in company_links:
            try:
                company_url = link.get('href')
                if not company_url.startswith('http'):
                    company_url = f"https://agrotender.com.ua{company_url}"
                
                if company_url in processed_urls:
                    continue
                processed_urls.add(company_url)
                
                card_text = link.get_text()
                
                company_name = None
                
                for tag in ["h2", "h3", "h4", "h5", "strong", "b"]:
                    elem = link.find(tag)
                    if elem:
                        name = elem.get_text(strip=True)
                        if name and not any(crop in name for crop in INTERESTED_CROPS) and not name.isdigit() and len(name) > 3:
                            company_name = name
                            break
                
                if not company_name:
                    lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                    if lines:
                        first_line = lines[0]
                        if not any(crop in first_line for crop in INTERESTED_CROPS) and not re.match(r'^\d+', first_line) and len(first_line) > 3:
                            company_name = first_line[:50]
                
                if not company_name:
                    company_name = "Трейдер з agrotender"
                
                try:
                    time.sleep(0.5)
                    company_page = requests.get(company_url, headers=headers, timeout=10)
                    company_soup = BeautifulSoup(company_page.text, "html.parser")
                    
                    is_actual = False
                    date_text = company_soup.get_text()
                    
                    for month_name, month_num in months_uk.items():
                        if month_name in date_text:
                            pattern = rf'(\d+)\s+{month_name}'
                            match = re.search(pattern, date_text)
                            if match:
                                day = int(match.group(1))
                                year = datetime.now().year
                                
                                try:
                                    price_date = datetime(year, month_num, day)
                                    days_old = (datetime.now() - price_date).days
                                    
                                    if days_old < 0:
                                        price_date = datetime(year - 1, month_num, day)
                                        days_old = (datetime.now() - price_date).days
                                    
                                    if days_old <= 7:
                                        is_actual = True
                                        break
                                except:
                                    pass
                    
                    if not is_actual:
                        continue
                    
                    tables = company_soup.find_all("table")
                    
                    found_in_table = False
                    for table in tables:
                        headers_row = table.find("tr")
                        if not headers_row:
                            continue
                        
                        cols = [th.get_text(strip=True) for th in headers_row.find_all(["th", "td"])]
                        
                        if not cols:
                            continue
                        
                        first_col = cols[0].lower()
                        if not any(keyword in first_col for keyword in ["регіон", "елеватор", "локація", "місце", "порт", "переход"]):
                            continue
                        
                        for row in table.find_all("tr")[1:]:
                            cells = row.find_all(["td", "th"])
                            if not cells:
                                continue
                            
                            location_text = cells[0].get_text(strip=True).replace("\xa0", " ")
                            if not location_text:
                                continue
                            
                            for i, col in enumerate(cols[1:], 1):
                                if i >= len(cells):
                                    continue
                                
                                if not col or len(col) < 3:
                                    continue
                                
                                cell = cells[i]
                                cell_text = cell.get_text(strip=True)
                                
                                price_match = re.search(r'(\d[\d\s]{2,10})', cell_text)
                                if not price_match:
                                    continue
                                
                                price_str = price_match.group(1).replace(" ", "").replace("\xa0", "")
                                
                                try:
                                    price = int(price_str)
                                except:
                                    continue
                                
                                if price < 100 or price > 100000:
                                    continue
                                
                                currency = "грн"
                                if price < 1000:
                                    currency = "дол"
                                
                                results.append({
                                    "date": datetime.now().strftime("%d.%m.%Y"),
                                    "contractor": company_name,
                                    "culture": col,
                                    "volume": "",
                                    "price": price,
                                    "currency": currency,
                                    "location": location_text,
                                    "contact": company_url,
                                    "source": "agrotender.com.ua",
                                })
                                found_in_table = True
                
                except Exception as e:
                    print(f"  Помилка обробки {company_url}: {e}")
                    continue
            
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"  Помилка: {e}")
    
    print(f"  Знайдено: {len(results)}")
    return results


def parse_graintrade():
    """Парсинг graintrade.com.ua"""
    print("Парсинг graintrade.com.ua...")
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
                    currency_text = price_match.group(2)
                    
                    currency = "грн" if "грн" in currency_text else "дол"
                    
                    location = cells[7].get_text(strip=True) if len(cells) >= 8 else ""
                    
                    results.append({
                        "date": date_cell,
                        "contractor": company,
                        "culture": culture,
                        "volume": volume,
                        "price": price,
                        "currency": currency,
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
    """Парсинг всіх джерел"""
    global prop_data, last_update
    
    print("\nПарсинг пропозицій...")
    all_results = []
    
    all_results.extend(parse_tripoli())
    all_results.extend(parse_agrofond())
    all_results.extend(parse_agrotender())
    all_results.extend(parse_graintrade())
    
    seen = set()
    unique_results = []
    
    for item in all_results:
        key = (
            item.get('contractor', ''),
            item.get('culture', ''),
            item.get('price', 0),
            item.get('location', ''),
            item.get('source', '')
        )
        
        if key not in seen:
            seen.add(key)
            unique_results.append(item)
    
    prop_data = unique_results
    last_update = datetime.now()
    
    print(f"\nВсього зібрано: {len(all_results)} пропозицій")
    print(f"Після видалення дублікатів: {len(unique_results)} пропозицій")
    
    try:
        import csv
        with open('prop_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
            if prop_data:
                fieldnames = ["date", "contractor", "culture", "volume", "price", "currency", "location", "contact", "source"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(prop_data)
        print("  Збережено у prop_data.csv")
    except Exception as e:
        print(f"  Помилка збереження: {e}")


def calculate_profit(offer, user_lat, user_lon, user_volume, vehicles):
    """
    Розраховує прибуток з урахуванням логістики через OSRM
    """
    offer_location = offer.get('location', '')
    
    offer_lat = offer.get('lat')
    offer_lon = offer.get('lon')
    
    if not offer_lat or not offer_lon:
        offer_lat, offer_lon = geocode_location(offer_location)
    
    if not offer_lat or not offer_lon:
        # Рахуємо дохід навіть без координат
        price = offer.get('price', 0)
        currency = offer.get('currency', 'грн')
        
        if currency == 'дол':
            price_uah = price * usd_rate
        else:
            price_uah = price
        
        income = user_volume * price_uah
        
        offer['distance'] = 0
        offer['income'] = round(income, 2)
        offer['logistics'] = 0
        offer['logistics_cost'] = 0
        offer['profit'] = round(income, 2)
        offer['price_uah'] = round(price_uah, 2)
        return offer
    
    print(f"\nРозрахунок для пропозиції: {offer['culture']} в {offer_location}")
    
    road_result = get_road_distance_osrm(user_lat, user_lon, offer_lat, offer_lon)
    
    if road_result:
        distance, duration = road_result
    else:
        print("  Використовую резервний розрахунок (пряма лінія)")
        distance = haversine(user_lat, user_lon, offer_lat, offer_lon)
    
    offer['distance'] = round(distance, 2)
    
    # Розраховуємо дохід
    price = offer.get('price', 0)
    currency = offer.get('currency', 'грн')
    
    if currency == 'дол':
        price_uah = price * usd_rate
    else:
        price_uah = price
    
    income = user_volume * price_uah
    offer['income'] = round(income, 2)
    offer['price_uah'] = round(price_uah, 2)
    
    if not vehicles:
        offer['logistics'] = 0
        offer['logistics_cost'] = 0
        offer['profit'] = round(income, 2)
        return offer
    
    best_cost = float('inf')
    
    for vehicle in vehicles:
        capacity = vehicle['capacity']
        rate = vehicle['rate']
        
        trips = math.ceil(user_volume / capacity)
        cost = trips * distance * 2 * rate
        
        if cost < best_cost:
            best_cost = cost
    
    offer['logistics_cost'] = round(best_cost, 2)
    
    price = offer.get('price', 0)
    currency = offer.get('currency', 'грн')
    
    if currency == 'дол':
        price_uah = price * usd_rate
        print(f"  Конвертація: {price} USD x {usd_rate} = {price_uah:.2f} грн")
    else:
        price_uah = price
    
    income = user_volume * price_uah
    logistics_cost = best_cost
    
    # Додаємо поля для відображення в таблиці
    offer['income'] = round(income, 2)
    offer['logistics'] = round(logistics_cost, 2)
    
    profit = income - logistics_cost
    offer['profit'] = round(profit, 2)
    offer['price_uah'] = round(price_uah, 2)
    
    return offer


def load_data_from_files():
    """Завантажує дані з файлів"""
    global prop_data, info_data
    
    if os.path.exists("prop_data.csv"):
        print("Завантаження prop_data.csv...")
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
                        "currency": row.get("currency", "грн"),
                        "location": row.get("location", ""),
                        "contact": row.get("contact", ""),
                        "source": row.get("source", "")
                    })
            print(f"  Завантажено {len(prop_data)} пропозицій")
        except Exception as e:
            print(f"  Помилка: {e}")
    
    if os.path.exists("info_data.json"):
        print("Завантаження info_data.json...")
        try:
            with open("info_data.json", 'r', encoding='utf-8') as f:
                info_data = json.load(f)
            print(f"  Завантажено інформацію про {len(info_data)} культур")
        except Exception as e:
            print(f"  Помилка: {e}")


def background_parsing():
    """Парсинг кожні 24 години"""
    while True:
        try:
            get_usd_rate()
            parse_all_proposals()
            print(f"Наступне оновлення через 24 години")
        except Exception as e:
            print(f"Помилка фонового парсингу: {e}")
        
        time.sleep(24 * 60 * 60)


def start_background_parsing():
    thread = threading.Thread(target=background_parsing, daemon=True)
    thread.start()


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
    
    for key, value in info_data.items():
        if culture.lower() in key.lower():
            stats['info'] = value
            break
    else:
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
    
    filtered.sort(key=lambda x: x.get('profit', 0) if x.get('profit') is not None else float('-inf'), reverse=True)
    
    user_filtered = []
    for user_offer in user_offers:
        if culture.lower() in user_offer['culture'].lower():
            offer_copy = user_offer.copy()
            calculate_profit(offer_copy, user_lat, user_lon, user_volume, vehicles)
            user_filtered.append(offer_copy)
    
    user_filtered.sort(key=lambda x: x.get('profit', 0) if x.get('profit') is not None else float('-inf'), reverse=True)
    
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
        "currency": data.get('currency', 'грн'),
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
    
    return jsonify({
        "success": True,
        "proposals_count": len(prop_data),
        "info_count": len(info_data),
        "last_update": last_update.strftime("%d.%m.%Y %H:%M") if last_update else "Немає даних"
    })


if __name__ == '__main__':
    print("=" * 60)
    print("ЗЕРНОВА ТОРГОВА ПЛАТФОРМА - БЕКЕНД З OSM")
    print("=" * 60)
    
    print("\nЗавантаження збережених даних...")
    load_data_from_files()
    
    if not prop_data:
        print("\nПочатковий парсинг...")
        parse_all_proposals()
    
    start_background_parsing()
    
    print("\n" + "=" * 60)
    print("Сервер запущено: http://localhost:5000")
    print("Фронтенд: frontend.html")
    print("\nГеокодування та відстані через OpenStreetMap")
    print("  Координати визначаються через OSM Nominatim")
    print("  Відстані рахуються по дорогах через OSRM")
    print("  Резервний словник для відомих локацій")
    print("=" * 60 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
