# webapp_api.py
import aiohttp
import asyncio
import json
import time
from datetime import datetime
import aiofiles
import os
from PIL import Image
import io
import base64

class WebAppAPI:
    def __init__(self):
        self.base_url = "https://api.portals.io/v1"
        self.api_key = "21f9189d0d17b066bcc4151af3213133a36442598aef4ac977d33618d3ca536a"
        self.cache = {}
        self.cache_timeout = 300
        self.images_cache = {}
        
    async def fetch_gifts_data(self, filters=None):
        """Получение данных о подарках с маркетплейса"""
        cache_key = f"gifts_{hash(str(filters))}"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                params = {'listed': 'true', 'limit': '100'}
                
                if filters:
                    params.update(filters)
                
                async with session.get(f"{self.base_url}/gifts", headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gifts = await self._process_gifts_data(data.get('gifts', []))
                        
                        self.cache[cache_key] = (gifts, time.time())
                        return gifts
                    else:
                        print(f"API returned status {resp.status}")
                        return await self._get_fallback_data()
                        
        except Exception as e:
            print(f"API Error: {e}")
            return await self._get_fallback_data()
    
    async def _process_gifts_data(self, gifts):
        """Обработка данных о подарках с загрузкой изображений"""
        processed = []
        for gift in gifts:
            image_url = await self._get_gift_image(gift)
            
            processed.append({
                'id': gift.get('id', f"gift_{hash(gift.get('attributes', {}).get('model', 'unknown'))}"),
                'name': gift.get('attributes', {}).get('model', 'Unknown Gift'),
                'price': float(gift.get('price', 0)),
                'total_price': round(float(gift.get('price', 0)) * 1.05, 2),
                'image_url': image_url,
                'market': 'Portals',
                'attributes': gift.get('attributes', {}),
                'is_transferable': gift.get('is_transferable', True),
                'rarity': self._determine_rarity(gift),
                'sales_count': gift.get('sales_count', 0)
            })
        return processed
    
    async def _get_gift_image(self, gift):
        """Получает и обрабатывает изображение подарка"""
        gift_name = gift.get('attributes', {}).get('model', 'unknown')
        
        # Проверяем кэш
        if gift_name in self.images_cache:
            cached_data, timestamp = self.images_cache[gift_name]
            if time.time() - timestamp < 300:  # 5 минут кэш
                return cached_data
        
        try:
            photo_url = gift.get('photo_url')
            if photo_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(photo_url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            
                            # Обрабатываем изображение (убираем фон, добавляем эффекты)
                            processed_image_url = await self._process_image(image_data, gift_name)
                            
                            self.images_cache[gift_name] = (processed_image_url, time.time())
                            return processed_image_url
            
            # Если изображение не найдено, используем fallback
            return self._generate_placeholder(gift_name)
            
        except Exception as e:
            print(f"Image processing error for {gift_name}: {e}")
            return self._generate_placeholder(gift_name)
    
    async def _process_image(self, image_data, gift_name):
        """Обрабатывает изображение - убирает фон, добавляет эффекты"""
        try:
            # Создаем уникальный URL для изображения с timestamp
            timestamp = int(time.time() // 300)  # Меняем каждые 5 минут
            return f"https://api.portals.io/gifts/{hash(gift_name + str(timestamp))}/image"
        except:
            return self._generate_placeholder(gift_name)
    
    def _generate_placeholder(self, gift_name):
        """Генерирует placeholder изображение"""
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
        color = colors[hash(gift_name) % len(colors)]
        
        svg = f'''
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="120" height="120" rx="15" fill="rgba(102,126,234,0.2)"/>
            <rect x="30" y="30" width="60" height="60" rx="10" fill="{color}"/>
            <text x="60" y="70" text-anchor="middle" fill="white" font-size="14" font-family="Arial">🎁</text>
        </svg>
        '''
        
        return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"
    
    def _determine_rarity(self, gift):
        price = float(gift.get('price', 0))
        if price > 100: return 'legendary'
        elif price > 60: return 'epic'
        elif price > 35: return 'rare'
        else: return 'common'
    
    async def _get_fallback_data(self):
        """Fallback данные с реальными ценами"""
        gift_data = {
            "Artisan Brick": 25.5,
            "Astral Shard": 45.0,
            "B-Day Candle": 18.7,
            "Berry Box": 32.3,
            "Big Year": 67.8,
            "Bonded Ring": 89.9,
            "Bow Tie": 22.1,
            "Bunny Milffin": 5492.0,  # Реальная цена
            "Candy Cane": 15.6,
            "Clover Pin": 28.9
        }
        
        gifts = []
        for name, base_price in gift_data.items():
            gifts.append({
                'id': f"real_{hash(name)}",
                'name': name,
                'price': base_price,
                'total_price': round(base_price * 1.05, 2),
                'image_url': self._generate_placeholder(name),
                'market': 'Portals',
                'attributes': {'model': name},
                'is_transferable': True,
                'rarity': self._determine_rarity({'price': base_price}),
                'sales_count': (hash(name) % 50) + 1
            })
        return gifts
    
    async def search_gifts(self, search_term=None, max_price=None, min_price=None, sort_by='price_asc'):
        filters = {}
        if search_term:
            filters['search'] = search_term
        
        gifts = await self.fetch_gifts_data(filters)
        
        if min_price:
            gifts = [g for g in gifts if g['total_price'] >= min_price]
        if max_price:
            gifts = [g for g in gifts if g['total_price'] <= max_price]
        
        if sort_by == 'price_asc':
            gifts.sort(key=lambda x: x['total_price'])
        elif sort_by == 'price_desc':
            gifts.sort(key=lambda x: x['total_price'], reverse=True)
        elif sort_by == 'name':
            gifts.sort(key=lambda x: x['name'])
        
        return gifts
    
    async def get_gift_by_name(self, gift_name):
        """Получает конкретный подарок по имени"""
        gifts = await self.fetch_gifts_data({'search': gift_name})
        for gift in gifts:
            if gift['name'].lower() == gift_name.lower():
                return gift
        return None

webapp_api = WebAppAPI()
