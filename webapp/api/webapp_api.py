# api/webapp_api.py
import aiohttp
import asyncio
import json
import time
from datetime import datetime
import aiofiles
import os
import base64
import hashlib

class WebAppAPI:
    def __init__(self):
        self.base_url = "https://api.portals.io/v1"
        self.api_key = "21f9189b0d17b066bcc4151af3213133a36442598aef4ac977d33618d3ca536a"
        self.cache = {}
        self.cache_timeout = 300
        self.images_cache = {}
        self.my_commission = 0.08
        self.market_commission = 0.05
        
    async def fetch_all_gifts(self):
        """Получение всех подарков с маркетплейса"""
        cache_key = "all_gifts"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data
        
        try:
            # Имитация API запроса
            await asyncio.sleep(1)
            
            # Используем fallback данные
            return await self._get_realistic_fallback_data()
                        
        except Exception as e:
            print(f"API Error: {e}")
            return await self._get_realistic_fallback_data()
    
    async def _process_gifts_data(self, gifts):
        """Обработка данных о подарках"""
        processed = []
        for gift in gifts:
            gift_name = gift.get('name', 'Unknown Gift')
            
            base_price = gift.get('base_price', 0)
            market_fee = base_price * self.market_commission
            my_fee = base_price * self.my_commission
            total_price = base_price + market_fee + my_fee
            
            processed.append({
                'id': gift.get('id', f"gift_{hash(gift_name)}"),
                'name': gift_name,
                'base_price': base_price,
                'market_fee': round(market_fee, 2),
                'my_fee': round(my_fee, 2),
                'total_price': round(total_price, 2),
                'image_url': gift.get('image_url', ''),
                'market': 'Portals',
                'attributes': gift.get('attributes', {}),
                'is_transferable': True,
                'rarity': gift.get('rarity', 'common'),
                'sales_count': gift.get('sales_count', 0)
            })
        
        return processed
    
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
    
    def _determine_rarity(self, price):
        if price > 100: return 'legendary'
        elif price > 60: return 'epic'
        elif price > 35: return 'rare'
        else: return 'common'
    
    async def _get_realistic_fallback_data(self):
        """Реалистичные fallback данные"""
        realistic_gifts = [
            "Artisan Brick", "Astral Shard", "B-Day Candle", "Berry Box", "Big Year",
            "Bonded Ring", "Bow Tie", "Bunny Milffin", "Candy Cane", "Clover Pin",
            "Cookie Heart", "Crystal Ball", "Cupid Charm", "Desk Calendar", "Diamond Ring",
            "Durov's Cap", "Easter Egg", "Electric Skull", "Eternal Candle", "Eternal Rose",
            "Evil Eye", "Flying Broom", "Fresh Socks", "Gem Signet", "Genie Lamp",
            "Ginger Cookie", "Hanging Star", "Heart Locket", "Heroic Helmet", "Hex Pot",
            "Holiday Drink", "Homemade Cake", "Hypno Lollipop", "Input Key", "Ion Gem",
            "Ionic Dryer", "Jack-in-the-Box", "Jelly Bunny", "Jester Hat", "Jingle Bells",
            "Jolly Chimp", "Joyful Bundle", "Kissed Frog", "Light Sword", "Lol Pop",
            "Loot Bag", "Love Candle", "Love Potion", "Low Rider", "Lunar Snake",
            "Lush Bouquet", "Mad Pumpkin", "Magic Potion", "Mighty Arm", "Mini Oscar",
            "Moon Pandante", "Nail Bracelet", "Neko Helmet", "Party Sparkler", "Perfume Bottle",
            "Pet Snake", "Plush Pepe", "Precious Peach", "Record Player", "Restless Jar",
            "Sakura Flower", "Santa Hat", "Scared Cat", "Sharp Tongue", "Signet Ring",
            "Skull Flower", "Sky Stilettos", "Sleigh Bell", "Snake Box", "Snoop Cigar",
            "Snoop Dogg", "Snow Globe", "Snow Mittens", "Spiced Wine", "Spy Agaric",
            "Star Notepad", "Stellar Rocket", "Swag Bag", "Swiss Watch", "Tama Gadget",
            "Top Hat", "Toy Bear", "Trapped Heart", "Valentine Box", "Vintage Cigar",
            "Voodoo Doll", "Westside Sign", "Whip Cupcake", "Winter Weath", "Witch Hat",
            "Xmas Strocking"
        ]
        
        gifts = []
        for name in realistic_gifts:
            base_price = self._get_realistic_price(name)
            market_fee = base_price * self.market_commission
            my_fee = base_price * self.my_commission
            total_price = base_price + market_fee + my_fee
            
            gifts.append({
                'id': f"real_{hash(name)}",
                'name': name,
                'base_price': base_price,
                'market_fee': round(market_fee, 2),
                'my_fee': round(my_fee, 2),
                'total_price': round(total_price, 2),
                'image_url': self._generate_placeholder(name),
                'market': 'Portals',
                'attributes': {'model': name},
                'is_transferable': True,
                'rarity': self._determine_rarity(base_price),
                'sales_count': (hash(name) % 50) + 1
            })
        return gifts
    
    def _get_realistic_price(self, gift_name):
        price_ranges = {
            "Bunny Milffin": 5000, "Plush Pepe": 4500, "Snoop Dogg": 4000, "Durov's Cap": 3500,
            "Diamond Ring": 150, "Eternal Rose": 120, "Crystal Ball": 100, "Genie Lamp": 90,
            "Astral Shard": 70, "Heroic Helmet": 60, "Magic Potion": 50, "Electric Skull": 45,
            "Artisan Brick": 25, "Candy Cane": 20, "Bow Tie": 18, "Fresh Socks": 15
        }
        
        if gift_name in price_ranges:
            return price_ranges[gift_name]
        
        base_price = (hash(gift_name) % 80) + 20
        return float(base_price)
    
    async def search_gifts(self, search_term=None, max_price=None, min_price=None, sort_by='price_asc'):
        """Поиск подарков"""
        all_gifts = await self.fetch_all_gifts()
        
        filtered_gifts = all_gifts
        
        if search_term:
            filtered_gifts = [g for g in filtered_gifts if search_term.lower() in g['name'].lower()]
        
        if min_price:
            filtered_gifts = [g for g in filtered_gifts if g['total_price'] >= min_price]
        if max_price:
            filtered_gifts = [g for g in filtered_gifts if g['total_price'] <= max_price]
        
        if sort_by == 'price_asc':
            filtered_gifts.sort(key=lambda x: x['total_price'])
        elif sort_by == 'price_desc':
            filtered_gifts.sort(key=lambda x: x['total_price'], reverse=True)
        
        return filtered_gifts

webapp_api = WebAppAPI()

# API endpoints
from .database import stats_db

async def register_activity_endpoint(data):
    try:
        user_id = data.get('user_id')
        username = data.get('username')
        
        if user_id:
            stats_db.register_user_activity(user_id, username)
            return {'success': True, 'message': 'Activity registered'}
        else:
            return {'success': False, 'error': 'User ID required'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def register_purchase_endpoint(data):
    try:
        user_id = data.get('user_id')
        username = data.get('username')
        gift_id = data.get('gift_id')
        gift_name = data.get('gift_name')
        amount = data.get('amount')
        
        if all([user_id, gift_id, gift_name, amount]):
            stats_db.register_purchase(user_id, username, gift_id, gift_name, amount)
            return {'success': True, 'message': 'Purchase registered'}
        else:
            return {'success': False, 'error': 'Missing required fields'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def get_statistics_endpoint():
    try:
        stats = stats_db.get_statistics()
        return {'success': True, 'data': stats}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def get_top_buyers_endpoint():
    try:
        buyers = stats_db.get_top_buyers()
        return {'success': True, 'data': buyers}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def get_popular_gifts_endpoint():
    try:
        gifts = stats_db.get_popular_gifts()
        return {'success': True, 'data': gifts}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def search_gifts_endpoint(data):
    try:
        search_term = data.get('search_term')
        max_price = data.get('max_price')
        min_price = data.get('min_price')
        
        gifts = await webapp_api.search_gifts(
            search_term=search_term,
            max_price=max_price,
            min_price=min_price
        )
        
        return {'success': True, 'data': gifts}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def get_all_gifts_endpoint():
    try:
        gifts = await webapp_api.fetch_all_gifts()
        return {'success': True, 'data': gifts}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def check_payment_endpoint(data):
    try:
        await asyncio.sleep(2)
        import random
        payment_found = random.random() < 0.7
        
        if payment_found:
            return {
                'success': True,
                'paid': True,
                'message': 'Оплата подтверждена'
            }
        else:
            return {
                'success': True,
                'paid': False,
                'message': 'Оплата не найдена'
            }
    except Exception as e:
        return {'success': False, 'message': f'Ошибка: {str(e)}'}

async def purchase_gift_endpoint(data):
    try:
        await asyncio.sleep(2)
        import random
        success = random.random() < 0.8
        
        if success:
            return {
                'success': True,
                'message': 'Подарок успешно приобретен'
            }
        else:
            return {
                'success': False,
                'message': 'Ошибка при покупке'
            }
    except Exception as e:
        return {'success': False, 'message': f'Ошибка: {str(e)}'}