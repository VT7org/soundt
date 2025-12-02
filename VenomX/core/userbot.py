from pyrogram import Client
import asyncio
import config
from ..logging import LOGGER

assistants = []
assistantids = []

GROUPS_TO_JOIN = [
    "BillaSpace",
    "BillaCore",
    "BillaNothing",
    "Storm_core",
    "storm_techh",
]


class Userbot:
    def __init__(self):
        self.one = Client(
            "SpaceXAss1",
            config.API_ID,
            config.API_HASH,
            session_string=str(config.STRING1),
            no_updates=True,
        )
        self.two = Client(
            "SpaceXAss2",
            config.API_ID,
            config.API_HASH,
            session_string=str(config.STRING2),
            no_updates=True,
        )
        self.three = Client(
            "SpaceXAss3",
            config.API_ID,
            config.API_HASH,
            session_string=str(config.STRING3),
            no_updates=True,
        )
        self.four = Client(
            "SpaceXAss4",
            config.API_ID,
            config.API_HASH,
            session_string=str(config.STRING4),
            no_updates=True,
        )
        self.five = Client(
            "SpaceXAss5",
            config.API_ID,
            config.API_HASH,
            session_string=str(config.STRING5),
            no_updates=True,
        )

    async def start_assistant(self, client: Client, index: int):
        string_attr = [
            config.STRING1,
            config.STRING2,
            config.STRING3,
            config.STRING4,
            config.STRING5,
        ][index - 1]
        if not string_attr:
            return

        try:
            await client.start()
            
            # Add small delay before joining groups to prevent rate limiting
            await asyncio.sleep(1)
            
            for group in GROUPS_TO_JOIN:
                try:
                    await client.join_chat(group)
                    await asyncio.sleep(0.5)  # Small delay between joins
                except Exception:
                    pass

            assistants.append(index)

            try:
                await client.send_message(
                    config.LOGGER_ID, f"🎶 ᴀssɪsᴛ #{index} — ᴏᴘᴜs ᴍᴜsɪᴄ ɴᴏᴡ ɪɴ ᴍᴏᴛɪᴏɴ"
                )
            except Exception:
                LOGGER(__name__).error(
                    f"Aʜʜ ᴀssɪsᴛᴀɴᴛ {index} ᴄᴀɴ'ᴛ ᴀᴄᴄᴇss ᴛʜᴇ ʟᴏɢ ɢʀᴏᴜᴘ. ᴘʀᴏᴍᴏᴛᴇ ᴛʜᴇᴍ ᴀs ᴀᴅᴍɪɴ"
                )
                exit()

            me = await client.get_me()
            client.id, client.name, client.username = me.id, me.first_name, me.username
            assistantids.append(me.id)

            LOGGER(__name__).info(f"ᴀssɪsᴛᴀɴᴛ {index} sᴛᴀʀᴛᴇᴅ ᴀs {client.name}")

        except Exception as e:
            LOGGER(__name__).error(f"Fᴀɪʟᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴀssɪsᴛᴀɴᴛ {index}: {e}")

    async def start(self):
        LOGGER(__name__).info("ᴇʟᴇɢᴀɴᴄᴇ ɪɴ sᴏᴜɴᴅ ɪs ᴏɴ ᴛʜᴇ ᴡᴀʏ , sᴛᴀʀᴛɪɴɢ ᴀssɪsᴛᴀɴᴛs..")
        
        # Stagger client starts to reduce concurrent load
        clients = [
            (self.one, 1),
            (self.two, 2),
            (self.three, 3),
            (self.four, 4),
            (self.five, 5)
        ]
        
        for client, index in clients:
            await self.start_assistant(client, index)
            await asyncio.sleep(2)  # 2-second delay between each client start

    async def stop(self):
        LOGGER(__name__).info("sᴛᴏᴘᴘɪɴɢ ᴛʜᴇ ᴇʟᴇɢᴀɴᴄʏ ᴏғ ᴏᴘᴜs ᴀssɪsᴛᴀɴᴛ ᴡɪᴛʜ ᴇᴀsᴇ...")
        try:
            # Stop clients with delays to prevent connection issues
            if config.STRING1:
                await self.one.stop()
                await asyncio.sleep(0.5)
            if config.STRING2:
                await self.two.stop()
                await asyncio.sleep(0.5)
            if config.STRING3:
                await self.three.stop()
                await asyncio.sleep(0.5)
            if config.STRING4:
                await self.four.stop()
                await asyncio.sleep(0.5)
            if config.STRING5:
                await self.five.stop()
        except Exception as e:
            LOGGER(__name__).error(f"Eʀʀᴏʀ ᴡʜɪʟᴇ sᴛᴏᴘɪɴɢ ᴀssɪsᴛᴀɴᴛ: {e}")
