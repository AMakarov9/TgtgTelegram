from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentType
from tgtg import TgtgClient
from datetime import datetime
from supabase import create_client
import asyncio, logging, os, signal, requests, threading, pytz, alltokens, location, handling
from time import strftime, gmtime
from urllib.parse import quote


SUPABASE_URL = alltokens.supabase_url
SUPABASE_KEY = alltokens.supabase_key
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = alltokens.BOT_TOKEN
ACCOUNT_EMAIL = alltokens.ACCOUNT_EMAIL

ACCESS_TOKEN = alltokens.access_token
REFRESH_TOKEN = alltokens.refresh_token
USER_ID = alltokens.user_id
COOKIE = alltokens.cookie

BOT = Bot(BOT_TOKEN, parse_mode = "HTML", disable_web_page_preview = True)
dp = Dispatcher(BOT)

user_state = dict()

logging.basicConfig (format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)



def sendM(id: str, message: str) -> None: 
    
    ''' Bot sends message to specific chat id'''

    message = quote(message)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={id}&text={message}"
    requests.get(url)

def create_tgtg_client() -> TgtgClient:
    
    if ACCESS_TOKEN == "": 
        client = TgtgClient(ACCOUNT_EMAIL)
        tokens = client.get_credentials()
        return client

    else: 
        client = TgtgClient(access_token = ACCESS_TOKEN, refresh_token = REFRESH_TOKEN, user_id = USER_ID, cookie = COOKIE)
        return client

def get_available_bags(client: TgtgClient) -> list: 
    favourites = client.get_items()
    available_bags = []

    for bag in favourites: 
        # Length greater than 12 indicates that bag is available
        if len(bag) > 12: 
            if bag['in_sales_window'] and bag['items_available'] > 0: 
                store_name = bag['store']['store_name']
                store_address = bag['store']['store_location']['address']['address_line']
                start_time = handling.convert_and_format_time(bag['pickup_interval']['start'])
                available_bags.append((store_name, store_address, start_time))
                logging.info(store_name+' is available')

    if len(available_bags) == 0: 
        return None

    else: 
        return available_bags

@dp.message_handler(commands = 'start')
async def command_start(message: types.Message): 
    user_state[message.chat.id] = 'start'
    response = supabase.table('test').select('chat_id').eq('chat_id', str(message.chat.id)).execute()

    if response.data == []: 
        supabase.table('users').insert({'chat_id': message.chat.id, 'first_name': message.chat.first_name}).execute()

        logging.info('Added user')
        await message.answer (text = 'You have been added to notification list')

    else: 
        await message.answer (text = 'You are already registered')


@dp.message_handler(commands = 'setaddress')
async def set_address(message: types.Message): 
    user_state[message.chat.id] = 'setaddress'
    await message.answer ('Send preferred starting pointfor tgtg pickups')

@dp.message_handler(content_types = ContentType.TEXT)
async def message(message: types.Message): 

    match user_state[message.chat.id]: 
        case 'setaddress': 
            address = quote(message.text)
            supabase.table('users').update({'default_location': encoded}).eq('chat_id', str(message.chat.id)).execute()
    
    logging.info('Address updated')

async def search_for_bags(client: TgtgClient):

    logging.info('entered search_for_bags')
    currently_available = []

    while True: 
        await asyncio.sleep(10)
        available_bags = get_available_bags(client)

        if available_bags != None: 
            data, count = supabase.table('users').select('chat_id', 'default_location').execute()

            for bag in available_bags: 
                if bag not in currently_available: 
                    
                    store_address = quote(bag[1])

                    start_time = bag[2]
              
                    for user in data[1]: 
                        try: 
                            logging.info('Sending notification')
                            chat_id = user['chat_id']
                            start_address = user['default_location']

                            # If user hasnt set address
                            if start_address == '': 
                                start_address = 'Forskningsparken'

                           
                            times_for_route = location.give_routes(start_time, start_address, store_address)
                            sendM(chat_id, f"https://www.google.com/maps/dir/?api=1&origin={start_address}&destination={store_address}&travelmode=transit")
                            sendM(chat_id, times_for_route)
                        
                            sendM(chat_id, f"{bag[0]} has put out a bag. Pickup options above.") 
                        except Exception as e: 
                            logging.info(e)
                            raise e

client = create_tgtg_client()
def runSearchBags(client = client): 
    print("searching bags")
    asyncio.run(search_for_bags(client))

def signal_handler(sig, frame): 
    def force_exit(): 
        print("Forcing stop of program")
        os.kill(os.getpid(), signal.SIGILL)
    force_exit()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    thread = threading.Thread(target = runSearchBags)
    thread.start()
    executor.start_polling(dp)
