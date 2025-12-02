import random
import inspect
from pytgcalls import PyTgCalls

from VenomX import userbot
from VenomX.core.mongo import mongodb

db = mongodb.assistants
assistantdict = {}


async def get_client(assistant: int):
    clients = userbot.clients
    if 1 <= assistant <= len(userbot.clients):
        return clients[assistant - 1]
    return None


async def save_assistant(chat_id, number):
    number = int(number)
    assistantdict[chat_id] = number
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": number}},
        upsert=True,
    )
    return await get_assistant(chat_id)


async def set_assistant(chat_id):
    from VenomX.core.userbot import assistants

    dbassistant = await db.find_one({"chat_id": chat_id})
    current_assistant = dbassistant["assistant"] if dbassistant else None

    available_assistants = [assi for assi in assistants if assi != current_assistant]

    if len(available_assistants) <= 1:
        ran_assistant = random.choice(assistants)
    else:
        ran_assistant = random.choice(available_assistants)

    assistantdict[chat_id] = ran_assistant
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": ran_assistant}},
        upsert=True,
    )

    userbot_client = await get_client(ran_assistant)
    return userbot_client


async def get_assistant(chat_id: int) -> str:
    from VenomX.core.userbot import assistants

    assistant = assistantdict.get(chat_id)
    if not assistant:
        dbassistant = await db.find_one({"chat_id": chat_id})
        if not dbassistant:
            userbot_client = await set_assistant(chat_id)
            return userbot_client
        else:
            got_assis = dbassistant["assistant"]
            if got_assis in assistants:
                assistantdict[chat_id] = got_assis
                userbot_client = await get_client(got_assis)
                return userbot_client
            else:
                userbot_client = await set_assistant(chat_id)
                return userbot_client
    else:
        if assistant in assistants:
            userbot_client = await get_client(assistant)
            return userbot_client
        else:
            userbot_client = await set_assistant(chat_id)
            return userbot_client


async def set_calls_assistant(chat_id):
    from VenomX.core.userbot import assistants

    ran_assistant = random.choice(assistants)
    assistantdict[chat_id] = ran_assistant
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": ran_assistant}},
        upsert=True,
    )
    return ran_assistant


async def group_assistant(self, chat_id: int) -> PyTgCalls:
    from VenomX.core.userbot import assistants

    assistant = assistantdict.get(chat_id)
    if not assistant:
        dbassistant = await db.find_one({"chat_id": chat_id})
        if not dbassistant:
            assis = await set_calls_assistant(chat_id)
        else:
            assis = dbassistant["assistant"]
            if assis in assistants:
                assistantdict[chat_id] = assis
            else:
                assis = await set_calls_assistant(chat_id)
    else:
        if assistant in assistants:
            assis = assistant
        else:
            assis = await set_calls_assistant(chat_id)

    assistant_index = int(assis) - 1

    calls_attr = self.calls

    if inspect.isawaitable(calls_attr):
        calls_list = await calls_attr
    else:
        if callable(calls_attr):
            result = calls_attr()
            if inspect.isawaitable(result):
                calls_list = await result
            else:
                calls_list = result
        else:
            calls_list = calls_attr

    try:
        if 0 <= assistant_index < len(calls_list):
            return calls_list[assistant_index]
    except TypeError:
        raise ValueError("Unable to determine call holders list; 'self.calls' is not iterable or has unexpected type.")
    raise ValueError(f"Assistant index {assistant_index + 1} is out of range.")
