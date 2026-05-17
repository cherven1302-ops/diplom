"""
Модуль для роботи з PostgreSQL базою даних
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

class Database:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL не знайдено в environment variables")
        
        # Render використовує postgres://, але psycopg2 потребує postgresql://
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Підключення до бази даних"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print("✓ Підключено до PostgreSQL")
            return True
        except Exception as e:
            print(f"✗ Помилка підключення до БД: {e}")
            return False
    
    def close(self):
        """Закрити з'єднання"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def init_schema(self):
        """Створити таблиці якщо не існують"""
        try:
            # Таблиця пропозицій
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    id SERIAL PRIMARY KEY,
                    date VARCHAR(20),
                    contractor VARCHAR(200),
                    culture VARCHAR(100),
                    volume VARCHAR(50),
                    price DECIMAL(10, 2),
                    currency VARCHAR(10),
                    location VARCHAR(200),
                    contact VARCHAR(200),
                    source VARCHAR(100),
                    lat DECIMAL(10, 6),
                    lon DECIMAL(10, 6),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Індекси
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_culture ON proposals(culture)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON proposals(date)")
            
            self.conn.commit()
            print("✓ Схема БД ініціалізована")
            return True
        except Exception as e:
            print(f"✗ Помилка ініціалізації схеми: {e}")
            self.conn.rollback()
            return False
    
    def save_proposals(self, proposals):
        """Зберегти пропозиції в БД"""
        try:
            # Очистити старі дані (старші 7 днів)
            self.cursor.execute("""
                DELETE FROM proposals 
                WHERE created_at < NOW() - INTERVAL '7 days'
            """)
            
            # Вставити нові
            for p in proposals:
                self.cursor.execute("""
                    INSERT INTO proposals 
                    (date, contractor, culture, volume, price, currency, location, contact, source, lat, lon)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    p.get('date', ''),
                    p.get('contractor', ''),
                    p.get('culture', ''),
                    p.get('volume', ''),
                    p.get('price', 0),
                    p.get('currency', 'грн'),
                    p.get('location', ''),
                    p.get('contact', ''),
                    p.get('source', ''),
                    p.get('lat'),
                    p.get('lon')
                ))
            
            self.conn.commit()
            print(f"✓ Збережено {len(proposals)} пропозицій в БД")
            return True
        except Exception as e:
            print(f"✗ Помилка збереження в БД: {e}")
            self.conn.rollback()
            return False
    
    def get_all_proposals(self):
        """Отримати всі пропозиції з БД"""
        try:
            self.cursor.execute("""
                SELECT date, contractor, culture, volume, price, currency, 
                       location, contact, source, lat, lon
                FROM proposals
                ORDER BY created_at DESC
            """)
            
            rows = self.cursor.fetchall()
            proposals = []
            
            for row in rows:
                proposals.append({
                    'date': row['date'],
                    'contractor': row['contractor'],
                    'culture': row['culture'],
                    'volume': row['volume'],
                    'price': float(row['price']) if row['price'] else 0,
                    'currency': row['currency'],
                    'location': row['location'],
                    'contact': row['contact'],
                    'source': row['source'],
                    'lat': float(row['lat']) if row['lat'] else None,
                    'lon': float(row['lon']) if row['lon'] else None
                })
            
            print(f"✓ Завантажено {len(proposals)} пропозицій з БД")
            return proposals
        except Exception as e:
            print(f"✗ Помилка читання з БД: {e}")
            return []
    
    def get_proposals_by_culture(self, culture):
        """Отримати пропозиції по культурі"""
        try:
            self.cursor.execute("""
                SELECT date, contractor, culture, volume, price, currency, 
                       location, contact, source, lat, lon
                FROM proposals
                WHERE LOWER(culture) LIKE %s
                ORDER BY price DESC
            """, (f'%{culture.lower()}%',))
            
            rows = self.cursor.fetchall()
            proposals = []
            
            for row in rows:
                proposals.append({
                    'date': row['date'],
                    'contractor': row['contractor'],
                    'culture': row['culture'],
                    'volume': row['volume'],
                    'price': float(row['price']) if row['price'] else 0,
                    'currency': row['currency'],
                    'location': row['location'],
                    'contact': row['contact'],
                    'source': row['source'],
                    'lat': float(row['lat']) if row['lat'] else None,
                    'lon': float(row['lon']) if row['lon'] else None
                })
            
            return proposals
        except Exception as e:
            print(f"✗ Помилка читання по культурі: {e}")
            return []
    
    def count_proposals(self):
        """Підрахунок кількості пропозицій"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM proposals")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
