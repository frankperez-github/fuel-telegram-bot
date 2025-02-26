import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
from scheduling import api_hash, api_id


session_name = 'fuel-try-session'

async def send_message(api_id, api_hash, group_username="", message=""):
    async with TelegramClient(session_name, api_id, api_hash) as client:
        return await client.send_message(group_username, message)


async def schedule_task(target_time, group_username, message_text, api_id, api_hash):
    try:
        # Use UTC time
        now = datetime.now(timezone.utc)
        target = datetime.strptime(target_time, "%H:%M:%S").replace(
            year=now.year, 
            month=now.month, 
            day=now.day,
            tzinfo=timezone.utc
        )
        
        if target < now:
            target += timedelta(days=1)
            
        delay = (target - now).total_seconds()
        
        if delay > 0:
            print(f"Scheduling message in {delay} seconds")
            await asyncio.sleep(delay)

        # Retry loop
        retry_count = 0
        max_retries = 1000
        while retry_count < max_retries:
            try:
                await send_message(group_username, message_text, api_id, api_hash)
                print("Message sent successfully")
                return
            except Exception as e:
                retry_count += 1
                print(f"Attempt {retry_count}/{max_retries} failed: {str(e)}")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)

        print(f"Failed to send message after {max_retries} attempts")

    except Exception as e:
        print(f"Error in scheduled message: {str(e)}")