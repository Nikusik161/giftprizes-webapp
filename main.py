# main.py
from aiohttp import web
import asyncio
import os
from database import stats_db
from webapp_api import *

async def handle_index(request):
    return web.FileResponse('./static/index.html')

async def handle_api(request):
    try:
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        if request.method == 'OPTIONS':
            return web.Response(status=200, headers=headers)
        
        # Parse data
        if request.method == 'POST':
            try:
                data = await request.json()
            except:
                data = {}
        else:
            data = dict(request.query)
        
        path = request.path
        
        # Route requests
        if '/register_activity' in path:
            result = await register_activity_endpoint(data)
        elif '/get_statistics' in path:
            result = await get_statistics_endpoint()
        elif '/get_top_buyers' in path:
            result = await get_top_buyers_endpoint()
        elif '/get_popular_gifts' in path:
            result = await get_popular_gifts_endpoint()
        elif '/search_gifts' in path:
            result = await search_gifts_endpoint(data)
        elif '/get_all_gifts' in path:
            result = await get_all_gifts_endpoint()
        elif '/check_payment' in path:
            result = await check_payment_endpoint(data)
        elif '/purchase_gift' in path:
            result = await purchase_gift_endpoint(data)
        elif '/generate_payment' in path:
            result = await generate_payment_endpoint(data)
        elif '/update_purchase_status' in path:
            result = await update_purchase_status_endpoint(data)
        elif '/get_button_status' in path:
            result = await get_button_status_endpoint(data)
        elif '/set_button_status' in path:
            result = await set_button_status_endpoint(data)
        else:
            result = {'success': False, 'error': 'Endpoint not found'}
        
        return web.json_response(result, headers=headers)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'success': False, 'error': str(e)}, headers=headers)

async def generate_payment_endpoint(data):
    return {
        'success': True, 
        'wallet_address': 'UQAaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'amount': data.get('amount', 0)
    }

async def update_purchase_status_endpoint(data):
    return {'success': True}

async def get_button_status_endpoint(data):
    button_id = data.get('button_id')
    return {'success': True, 'enabled': True}

async def set_button_status_endpoint(data):
    return {'success': True}

def init_app():
    app = web.Application()
    
    # Routes
    app.router.add_get('/', handle_index)
    app.router.add_get('/index.html', handle_index)
    app.router.add_post('/api/{endpoint:.*}', handle_api)
    app.router.add_get('/api/{endpoint:.*}', handle_api)
    
    return app

if __name__ == '__main__':
    app = init_app()
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, host='0.0.0.0', port=port)
