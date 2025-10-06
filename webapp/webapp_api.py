# webapp_api.py
import aiohttp
import asyncio
import json
import time
from datetime import datetime

class WebAppAPI:
    def __init__(self):
        self.base_url = "https://api.portals.io/v1"
        self.api_key = "21f9189d0d17b066bcc4151af3213133a36442598aef4ac977d33618d3ca536a"  # Замените на ваш ключ
        self.cache = {}
        self.cache_timeout = 300  # 5 минут
        
    async def fetch_gifts_data(self, filters=None):
        """Получение данных о подарках с маркетплейса"""
        cache_key = f"gifts_{hash(str(filters))}"
        
        # Проверяем кэш
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                params = {'listed': 'true', 'limit': '50'}
                
                if filters:
                    params.update(filters)
                
                async with session.get(f"{self.base_url}/gifts", headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gifts = self._process_gifts_data(data.get('gifts', []))
                        
                        # Сохраняем в кэш
                        self.cache[cache_key] = (gifts, time.time())
                        return gifts
                    else:
                        return self._get_fallback_data()
                        
        except Exception as e:
            print(f"API Error: {e}")
            return self._get_fallback_data()
    
    def _process_gifts_data(self, gifts):
        """Обработка данных о подарках"""
        processed = []
        for gift in gifts:
            processed.append({
                'id': gift.get('id'),
                'name': gift.get('attributes', {}).get('model', 'Unknown'),
                'price': float(gift.get('price', 0)),
                'total_price': round(float(gift.get('price', 0)) * 1.05, 2),
                'image_url': gift.get('photo_url'),
                'market': 'Portals',
                'attributes': gift.get('attributes', {}),
                'is_transferable': gift.get('is_transferable', True),
                'rarity': self._determine_rarity(gift)
            })
        return processed
    
    def _determine_rarity(self, gift):
        """Определение редкости подарка"""
        price = float(gift.get('price', 0))
        if price > 100:
            return 'legendary'
        elif price > 60:
            return 'epic'
        elif price > 35:
            return 'rare'
        else:
            return 'common'
    
    def _get_fallback_data(self):
        """Fallback данные если API недоступно"""
        gift_names = [
            "Artisan Brick", "Astral Shard", "B-Day Candle", "Berry Box", "Big Year",
            "Bonded Ring", "Bow Tie", "Bunny Milffin", "Candy Cane", "Clover Pin"
        ]
        
        gifts = []
        for name in gift_names:
            base_price = 20 + hash(name) % 60
            gifts.append({
                'id': f"fallback_{hash(name)}",
                'name': name,
                'price': base_price,
                'total_price': round(base_price * 1.05, 2),
                'image_url': None,
                'market': 'Fallback',
                'attributes': {'model': name},
                'is_transferable': True,
                'rarity': self._determine_rarity({'price': base_price})
            })
        return gifts
    
    async def search_gifts(self, search_term=None, max_price=None, min_price=None, sort_by='price_asc'):
        """Поиск подарков по критериям"""
        filters = {}
        if search_term:
            filters['attributes[model]'] = search_term
        
        gifts = await self.fetch_gifts_data(filters)
        
        # Фильтрация по цене
        if min_price:
            gifts = [g for g in gifts if g['total_price'] >= min_price]
        if max_price:
            gifts = [g for g in gifts if g['total_price'] <= max_price]
        
        # Сортировка
        if sort_by == 'price_asc':
            gifts.sort(key=lambda x: x['total_price'])
        elif sort_by == 'price_desc':
            gifts.sort(key=lambda x: x['total_price'], reverse=True)
        elif sort_by == 'name':
            gifts.sort(key=lambda x: x['name'])
        
        return gifts
    
    async def get_gift_details(self, gift_id):
        """Получение деталей конкретного подарка"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                async with session.get(f"{self.base_url}/gifts/{gift_id}", headers=headers) as resp:
                    if resp.status == 200:
                        gift = await resp.json()
                        return self._process_gifts_data([gift])[0]
                    else:
                        return None
        except:
            return None

# Создаем глобальный экземпляр API
webapp_api = WebAppAPI()
