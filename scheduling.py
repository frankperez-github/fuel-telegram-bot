# scheduling.py
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient
import pytz 

# Existing Telethon client setup

session_name = 'fuel-try-session'

# Timezone setup
NY_TZ = pytz.timezone('America/New_York')

async def send_message(api_id, api_hash, group_username="", message=""):
    async with TelegramClient(session_name, api_id, api_hash) as client:
        await client.send_message(group_username, message)

async def schedule_task(target_time, group_username, message_text, api_id, api_hash):
    try:
        # Get current time in New York timezone
        now = datetime.now(NY_TZ)
        
        # Parse target time and set to today's date in New York timezone
        target = NY_TZ.localize(
            datetime.strptime(target_time, "%H:%M:%S").replace(
                year=now.year,
                month=now.month,
                day=now.day
            )
        )
        
        # If target time has already passed today, schedule for tomorrow
        if target < now:
            target += timedelta(days=1)
            
        # Calculate delay in seconds
        delay = (target - now).total_seconds()
        
        if delay > 0:
            print(f"Scheduling message in {delay} seconds")
            await asyncio.sleep(delay)
        
        max_retries = 1000
        while max_retries > 0:
            max_retries-=1
            try:
                await send_message(api_id, api_hash, group_username=group_username, message=message_text)
                print("Message sent successfully!")
                break  # Exit loop on success.
            except Exception as e:
                print(f"Error sending message (retrying in 5 seconds): {e}")
                await asyncio.sleep(5)
                
    except Exception as e:
        print(f"Error in scheduled message: {e}")
