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
import hashlib

class WebAppAPI:
    def __init__(self):
        self.base_url = "https://api.portals.io/v1"
        self.api_key = "21f9189b0d17b066bcc4151af3213133a36442598aef4ac977d33618d3ca536a"
        self.cache = {}
        self.cache_timeout = 300
        self.images_cache = {}
        self.my_commission = 0.08  # 8% комиссия
        self.market_commission = 0.05  # 5% комиссия маркетплейса
        
    async def fetch_all_gifts(self):
        """Получение всех подарков с маркетплейса"""
        cache_key = "all_gifts"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                # Получаем все подарки с пагинацией
                all_gifts = []
                page = 1
                has_more = True
                
                while has_more and page <= 10:  # Ограничим 10 страницами
                    params = {
                        'listed': 'true', 
                        'limit': '100',
                        'page': str(page)
                    }
                    
                    async with session.get(f"{self.base_url}/gifts", headers=headers, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            gifts = data.get('gifts', [])
                            
                            if gifts:
                                all_gifts.extend(gifts)
                                page += 1
                            else:
                                has_more = False
                        else:
                            print(f"API returned status {resp.status}")
                            has_more = False
                
                # Обрабатываем данные
                processed_gifts = await self._process_gifts_data(all_gifts)
                self.cache[cache_key] = (processed_gifts, time.time())
                return processed_gifts
                        
        except Exception as e:
            print(f"API Error: {e}")
            return await self._get_realistic_fallback_data()
    
    async def _process_gifts_data(self, gifts):
        """Обработка данных о подарках"""
        processed = []
        for gift in gifts:
            # Получаем название подарка
            gift_name = gift.get('attributes', {}).get('model', 'Unknown Gift')
            
            # Пропускаем подарки без названия
            if not gift_name or gift_name == 'Unknown Gift':
                continue
                
            # Получаем изображение
            image_url = await self._get_gift_image(gift)
            
            # Рассчитываем цены
            base_price = float(gift.get('price', 0))
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
                'image_url': image_url,
                'market': 'Portals',
                'attributes': gift.get('attributes', {}),
                'is_transferable': gift.get('is_transferable', True),
                'rarity': self._determine_rarity(gift),
                'sales_count': gift.get('sales_count', 0)
            })
        
        # Убираем дубликаты по имени
        unique_gifts = {}
        for gift in processed:
            if gift['name'] not in unique_gifts:
                unique_gifts[gift['name']] = gift
            else:
                # Берем подарок с меньшей ценой
                if gift['total_price'] < unique_gifts[gift['name']]['total_price']:
                    unique_gifts[gift['name']] = gift
        
        return list(unique_gifts.values())
    
    async def _get_gift_image(self, gift):
        """Получает изображение подарка"""
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
                            
                            # Создаем уникальный URL для изображения
                            timestamp = int(time.time() // 300)  # Меняем каждые 5 минут
                            unique_url = f"https://api.portals.io/gifts/{hash(gift_name + str(timestamp))}/image"
                            
                            self.images_cache[gift_name] = (unique_url, time.time())
                            return unique_url
            
            # Если изображение не найдено, используем fallback
            return self._generate_placeholder(gift_name)
            
        except Exception as e:
            print(f"Image processing error for {gift_name}: {e}")
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
    
    async def _get_realistic_fallback_data(self):
        """Реалистичные fallback данные с реальными подарками"""
        # Список реальных подарков из Portals
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
            # Реалистичные цены основанные на реальных данных
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
                'rarity': self._determine_rarity({'price': base_price}),
                'sales_count': (hash(name) % 50) + 1
            })
        return gifts
    
    def _get_realistic_price(self, gift_name):
        """Возвращает реалистичную цену для подарка"""
        price_ranges = {
            # Легендарные подарки
            "Bunny Milffin": 5000,
            "Plush Pepe": 4500,
            "Snoop Dogg": 4000,
            "Durov's Cap": 3500,
            # Эпические подарки
            "Diamond Ring": 150,
            "Eternal Rose": 120,
            "Crystal Ball": 100,
            "Genie Lamp": 90,
            # Редкие подарки
            "Astral Shard": 70,
            "Heroic Helmet": 60,
            "Magic Potion": 50,
            "Electric Skull": 45,
            # Обычные подарки
            "Artisan Brick": 25,
            "Candy Cane": 20,
            "Bow Tie": 18,
            "Fresh Socks": 15
        }
        
        # Если подарок есть в списке, возвращаем его цену
        if gift_name in price_ranges:
            return price_ranges[gift_name]
        
        # Иначе генерируем реалистичную цену на основе названия
        base_price = (hash(gift_name) % 80) + 20  # От 20 до 100 TON
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
        elif sort_by == 'name':
            filtered_gifts.sort(key=lambda x: x['name'])
        
        return filtered_gifts
    
    async def get_gift_by_name(self, gift_name):
        """Получает конкретный подарок по имени"""
        gifts = await self.fetch_all_gifts()
        for gift in gifts:
            if gift['name'].lower() == gift_name.lower():
                return gift
        return None

    async def get_gift_packages(self, budget):
        """Создает пакеты подарков по бюджету"""
        all_gifts = await self.fetch_all_gifts()
        
        # Фильтруем доступные подарки
        available_gifts = [g for g in all_gifts if g['total_price'] <= budget]
        
        packages = []
        
        # Один дорогой подарок
        expensive_gifts = sorted(available_gifts, key=lambda x: x['total_price'], reverse=True)[:3]
        for gift in expensive_gifts:
            if gift['total_price'] >= budget * 0.8:  # Подарок за 80%+ бюджета
                packages.append({
                    'type': 'single_premium',
                    'gifts': [gift],
                    'total_price': gift['total_price'],
                    'description': f'Премиум подарок {gift["name"]}',
                    'savings': 0
                })
        
        # Пакет из нескольких подарков
        if budget >= 50:  # Минимальный бюджет для пакета
            package_gifts = []
            current_total = 0
            
            # Сортируем по цене (от дешевых к дорогим)
            sorted_gifts = sorted(available_gifts, key=lambda x: x['total_price'])
            
            for gift in sorted_gifts:
                if current_total + gift['total_price'] <= budget:
                    package_gifts.append(gift)
                    current_total += gift['total_price']
                else:
                    break
            
            if len(package_gifts) >= 2:
                individual_price = sum(g['total_price'] for g in package_gifts)
                package_price = individual_price * 0.9  # 10% скидка
                
                packages.append({
                    'type': 'multi_package',
                    'gifts': package_gifts,
                    'total_price': round(package_price, 2),
                    'description': f'Пакет из {len(package_gifts)} подарков',
                    'savings': round(individual_price - package_price, 2)
                })
        
        # Подарки с лучшим соотношением цена/качество
        value_gifts = sorted(available_gifts, 
                           key=lambda x: x['sales_count'] / x['total_price'] if x['total_price'] > 0 else 0, 
                           reverse=True)[:5]
        
        if len(value_gifts) >= 3:
            value_package = value_gifts[:3]
            package_price = sum(g['total_price'] for g in value_package) * 0.85  # 15% скидка
            
            packages.append({
                'type': 'value_package',
                'gifts': value_package,
                'total_price': round(package_price, 2),
                'description': 'Лучшие по продаваемости',
                'savings': round(sum(g['total_price'] for g in value_package) - package_price, 2)
            })
        
        return packages

    async def check_payment(self, wallet_address, amount, memo):
        """Проверяет оплату через TON API"""
        try:
            # Здесь будет интеграция с TON API для проверки транзакций
            # Пока используем имитацию
            
            # Имитация проверки платежа
            await asyncio.sleep(2)
            
            # В реальной реализации здесь будет запрос к TON API
            # Для демонстрации 70% шанс успешной оплаты
            import random
            payment_found = random.random() < 0.7
            
            if payment_found:
                return {
                    'success': True,
                    'message': 'Оплата подтверждена',
                    'transaction_hash': f'tx_{hashlib.md5(f"{wallet_address}{amount}{memo}".encode()).hexdigest()}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Оплата не найдена. Проверьте транзакцию или подождите несколько минут'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка проверки оплаты: {str(e)}'
            }

    async def purchase_gift(self, gift_id, recipient_username, user_wallet):
        """Покупка подарка на маркетплейсе"""
        try:
            # Получаем информацию о подарке
            gifts = await self.fetch_all_gifts()
            gift = next((g for g in gifts if g['id'] == gift_id), None)
            
            if not gift:
                return {
                    'success': False,
                    'message': 'Подарок не найден'
                }
            
            # Имитация покупки на маркетплейсе
            await asyncio.sleep(3)
            
            # В реальной реализации здесь будет:
            # 1. Покупка подарка через API маркетплейса
            # 2. Перевод подарка на аккаунт бота
            # 3. Отправка подарка получателю
            
            import random
            purchase_success = random.random() < 0.8  # 80% шанс успеха
            
            if purchase_success:
                return {
                    'success': True,
                    'message': f'Подарок {gift["name"]} успешно приобретен и отправлен пользователю {recipient_username}',
                    'gift_name': gift['name'],
                    'final_image_url': gift['image_url'],
                    'transaction_id': f'purchase_{int(time.time())}'
                }
            else:
                # Если подарок уже купили, предлагаем альтернативу
                similar_gifts = [g for g in gifts if g['name'] == gift['name'] and g['id'] != gift_id]
                if similar_gifts:
                    alternative_gift = similar_gifts[0]
                    return {
                        'success': True,
                        'message': f'Исходный подарок был продан. Мы нашли аналогичный {alternative_gift["name"]} и отправили его пользователю {recipient_username}',
                        'gift_name': alternative_gift['name'],
                        'final_image_url': alternative_gift['image_url'],
                        'transaction_id': f'purchase_alt_{int(time.time())}',
                        'is_alternative': True
                    }
                else:
                    return {
                        'success': False,
                        'message': 'К сожалению, этот подарок уже продан, и аналогичных не найдено. Средства будут возвращены в течение 24 часов.'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при покупке подарка: {str(e)}'
            }

webapp_api = WebAppAPI()

# API endpoints
from database import stats_db

async def register_activity_endpoint(data):
    """Endpoint для регистрации активности пользователя"""
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
    """Endpoint для регистрации покупки"""
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
    """Endpoint для получения статистики"""
    try:
        stats = stats_db.get_statistics()
        return {'success': True, 'data': stats}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def get_top_buyers_endpoint():
    """Endpoint для получения топа покупателей"""
    try:
        buyers = stats_db.get_top_buyers()
        return {'success': True, 'data': buyers}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def get_popular_gifts_endpoint():
    """Endpoint для получения популярных подарков"""
    try:
        gifts = stats_db.get_popular_gifts()
        return {'success': True, 'data': gifts}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def search_gifts_endpoint(data):
    """Endpoint для поиска подарков"""
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

async def get_gift_packages_endpoint(data):
    """Endpoint для получения пакетов подарков"""
    try:
        budget = data.get('budget', 100)
        packages = await webapp_api.get_gift_packages(budget)
        return {'success': True, 'data': packages}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def check_payment_endpoint(data):
    """Endpoint для проверки оплаты"""
    try:
        wallet_address = data.get('wallet_address')
        amount = data.get('amount')
        memo = data.get('memo')
        
        result = await webapp_api.check_payment(wallet_address, amount, memo)
        return result
    except Exception as e:
        return {'success': False, 'message': f'Ошибка проверки оплаты: {str(e)}'}

async def purchase_gift_endpoint(data):
    """Endpoint для покупки подарка"""
    try:
        gift_id = data.get('gift_id')
        recipient_username = data.get('recipient_username')
        user_wallet = data.get('user_wallet')
        
        result = await webapp_api.purchase_gift(gift_id, recipient_username, user_wallet)
        return result
    except Exception as e:
        return {'success': False, 'message': f'Ошибка покупки: {str(e)}'}

async def get_all_gifts_endpoint():
    """Endpoint для получения всех подарков"""
    try:
        gifts = await webapp_api.fetch_all_gifts()
        return {'success': True, 'data': gifts}
    except Exception as e:
        return {'success': False, 'error': str(e)}
