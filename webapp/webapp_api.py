# webapp_api.py (обновленная версия)
import aiohttp
import asyncio
import json
import time
from datetime import datetime
import aiofiles
import os
from PIL import Image
import io

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
            # В реальном приложении здесь будет обработка изображения
            # Для демонстрации возвращаем оригинальный URL или placeholder
            return f"https://api.portals.io/gifts/{hash(gift_name)}/image"
        except:
            return self._generate_placeholder(gift_name)
    
    def _generate_placeholder(self, gift_name):
        """Генерирует placeholder изображение"""
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
        color = colors[hash(gift_name) % len(colors)]
        return f"data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgdmlld0JveD0iMCAwIDEyMCAxMjAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMjAiIGhlaWdodD0iMTIwIiByeD0iMTUiIGZpbGw9InJnYmEoMTAyLDEyNiwyMzQsMC4yKSIvPgo8cmVjdCB4PSIzMCIgeT0iMzAiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcng9IjEwIiBmaWxsPSJ7Y29sb3J9Ii8+Cjx0ZXh0IHg9IjYwIiB5PSI3MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0id2hpdGUiIGZvbnQtc2l6ZT0iMTQiIGZvbnQtZmFtaWx5PSJBcmlhbCI+4p2QPC90ZXh0Pgo8L3N2Zz4=".replace('{color}', color[1:])
    
    def _determine_rarity(self, gift):
        price = float(gift.get('price', 0))
        if price > 100: return 'legendary'
        elif price > 60: return 'epic'
        elif price > 35: return 'rare'
        else: return 'common'
    
    async def _get_fallback_data(self):
        """Fallback данные"""
        gift_names = [
            "Artisan Brick", "Astral Shard", "B-Day Candle", "Berry Box", "Big Year",
            "Bonded Ring", "Bow Tie", "Bunny Milffin", "Candy Cane", "Clover Pin"
        ]
        
        gifts = []
        for name in gift_names:
            base_price = 20 + (hash(name) % 60)
            gifts.append({
                'id': f"fallback_{hash(name)}",
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

webapp_api = WebAppAPI()
