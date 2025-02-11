#Import libs
import telethon
from telethon.tl.custom import Button
from telethon import TelegramClient, events, sync

import asyncio #for async functions
import openai #for openai api
import config #py file to contain config settings for askcaibot

#config openai api
openai.api_key = config.openai_key

#config tele client
client  = TelegramClient('askcai', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

#define button stuff
keyboard_stop = [[Button.inline("Stop and reset conversation", b"stop")]]

#function to send question and get result
async def send_question_and_get_result(prompt, conv, keyboard):
    message = await conv.send_message(prompt, buttons = keyboard)
    
    loop = asyncio.get_event_loop()
    
    task1 = loop.create_task(
        conv.wait_event(events.CallbackQuery())
    )
    task2 = loop.create_task(
        conv.get_response()
    )

    #wait for either the user to tap a button or send a message
    done, _ = await asyncio.wait({task1, task2}, return_when=asyncio.FIRST_COMPLETED)
    
    #retrieve the result of the completed coroutine and delete the sent message
    result = done.pop().result()
    await message.delete()
    
    #return the user's response or None if they tapped a button
    if isinstance(result, events.CallbackQuery.Event):
        return None
    else:
        return result.message.strip()

#main chatbot handler
@client.on(events.NewMessage(pattern="/start"))
async def handler_start_command(event):
    SENDER = event.sender_id
    prompt = "hello i am askcai."

    #exception handling
    try:
        await client.send_message(SENDER, prompt)

        async with client.conversation(await event.get_chat(), exclusive = True, timeout=600) as conv:
            history = [] #history of messages

            while True: 
                #prompt user input
                prompt = "okay tell me what you want."
                user_input = await send_question_and_get_result(prompt, conv, keyboard_stop)

                #check if user wants to stop
                if user_input is None:
                    prompt = "okay. im out. /start to start again."
                    await client.send_message(SENDER, prompt)
                    break
                else: 
                    prompt = "okay noted. holup and lemme cook"
                    thinking = await client.send_message(SENDER, prompt)

                    history.append({"role":"user","content":user_input}) #append user input to history

                    #generate chat completion
                    chat_completion = openai.ChatCompletion.create(
                    model=config.model_engine,
                    messages=history,
                    max_tokens=100,
                    n=1,
                    temperature=0.1
                    )


                    response = chat_completion.choices[0].message.content #get response from chat completion
                    history.append({"role":"assistant","content":response})
                    await thinking.delete() #delete thinking message
                    await client.send_message(SENDER, response, parse_mode="Markdown")





    except asyncio.TimeoutError:
        await client.send_message(SENDER, "why respond so slow? /start to start again.")
        return

    except telethon.errors.common.AlreadyInConversationError:
        pass

    except Exception as e:
        print(e)
        await client.send_message(SENDER, "something went wrong. /start to start again.")
        return

#main
if __name__ == "__main__":
    print("AskCai is waking up from his slumber...")
    client.run_until_disconnected() #this starts the bot