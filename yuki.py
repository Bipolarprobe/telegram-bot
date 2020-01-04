#! /home/pi/python-projects/telegram-bot/bin/python3.8

from telegram import ext
from configparser import ConfigParser
from time import sleep
import threading
import aniquery
import json
import random

# load list of food options stored in json for long term storage
with open("food.json", 'r') as f:
    food_options = json.load(f)

# constant 10 minute default poll time
POLL_TIME = 600

# global variable for tracking number of unauthorized stop calls
STOP_CALLS = 0

# make config parser to read cfg with bot token
config = ConfigParser()
config.read("config.cfg")
yuki = config.get("tokens", "yuki")

# telegram bot updater class which handles updates and sends them to dispatcher
updater = ext.Updater(token=yuki, use_context=True)

# dispatcher class deals with sending updates to handlers
dispatcher = updater.dispatcher

# first handler function, all needing the same basic format
# this function handles the /start command from users
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hey friendos, I'm back, new and (hopefully) improved! Try out some of my new features. /help will give you a list of commands.")

# creating handler to be given to dispatcher
# CommandHandler is used to tie function to /start command
# function is named after command for clarity
start_handler = ext.CommandHandler("start", start)


# dictionary of help messages to organize help command and give greater detail
help_messages = {"food": "I'll give you some inspiration for what to cook tonight.",
"list": "This command will give you a list of all the food I know of already.",
"vote": "Call this command followed by a food item and I'll send you a poll where everyone can vote on what they want.",
"add": "Call this command followed by a food item and I'll add it to my list that I know for my /food option.",
"remove": "Call this with a food item in my current list to have it removed.",
"recommend": "This command will get me to give you a random show from the current season with an average score above 70 you may want to check out. You can also optionally follow this with a season (winter, spring, summer, fall), year, and minimum score.",
"stop": "This shuts me down if called by someone with administrative priveleges over me."
}


def help(update, context):
    # checks if any arguments follow the /help command
    if context.args:
        # tries to find help command that matches given argument
        context.bot.send_message(update.effective_chat.id,
                                text=help_messages.get(context.args[0].lower().lstrip('/'), "Not a valid command, try /help to get a list of commands."))
    else:
        # if /help is called alone gives a list of available commands
        commands = '/' + '\n/'.join(help_messages.keys())
        message = "Call help followed by a command name to get more info:\n"
        context.bot.send_message(update.effective_chat.id,
                                text=message + commands)

help_handler = ext.CommandHandler("help", help)

# command for getting random food recommendation from available options
def food(update, context):
    
    item = random.choice(food_options)
    
    message = f"How about some {item} tonight?"
    
    context.bot.send_message(chat_id=update.effective_chat.id,
                            text=message)
                            
food_handler = ext.CommandHandler("food", food)

# shows all known foods
def food_list(update, context):
    foods = ", ".join(food_options)
    message = f"Here's all the food I know of: {foods}"
    context.bot.send_message(chat_id=update.effective_chat.id,
                            text=message)

list_handler = ext.CommandHandler("list", food_list)

# command allows users to add new food items to food.json
def add(update, context):
    if context.args:
        # food items can be strings of arbitrary length
        new_item= ' '.join(context.args)
        # all items are sanitized to lowercase to attempt to avoid repeats
        new_item = new_item.lower()
        
        
        if new_item not in food_options:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"Okay! I'll add {new_item} to my food options.")
            
            # after sending confirmation item is added to list in memory
            # which is then written back to food.json for persistent storage
            food_options.append(new_item)
            with open("food.json", 'w') as f:
                json.dump(food_options, f)
        else:
            # if food item already exists nothing is added
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"I already have {new_item} in my options.")
    else:
        # if no arguments are provided an error message is sent to the user
        context.bot.send_message(update.effective_chat.id,
                                text="I'll need something you want to add")

add_handler = ext.CommandHandler("add", add)

# remove unwanted food items by name
def remove(update, context):
    if context.args:
        # if arguments provided, constructs and sanitizes string of args
        target = ' '.join(context.args)
        target = target.lower()
        
        if target in food_options:
            # if string is found in list, it is removed by name
            food_options.remove(target)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"Okay, I got rid of {target} from my food options.")
            
            # item removal is written to food.json for long term storage
            with open("food.json", 'w') as f:
                json.dump(food_options, f)

        else:
            # sends message if target string is not found in food_options
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"It looks like {target} isn't in my food options.")
    else:
        # sends error message to user if no arguments are provided
        context.bot.send_message(chat_id=update.effective_chat.id,
                                text="You'll need to actually tell me what you want removed")
                                
                                
remove_handler = ext.CommandHandler("remove", remove)

# function for closing a poll after given delay meant to be called
# in a separate thread when a poll starts
# message argument is the message object returned by the start poll call
def end_vote(update, context, message, delay):
    sleep(delay)
    results = context.bot.stop_poll(chat_id=update.effective_chat.id,
                        message_id=message.message_id)
    options = ""
    for poll_option in results.options:
        options += f"\n{poll_option.text}: {poll_option.voter_count}"
    
    text = f"Here's the results:{options}"
    context.bot.send_message(chat_id=update.effective_chat.id,
                            text=text)

# voting command which starts a poll which users can vote on
def vote(update, context):
    if context.args:
        item = ' '.join(context.args)
        text = f"Would you like {item} for dinner tonight?"
        message = context.bot.send_poll(
                                        chat_id=update.effective_chat.id,
                                        question=text,
                                        options=["Yes", "No"])
        threading.Thread(target=end_vote, args=(update, context, message, POLL_TIME)).start()
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                text="We can't vote if you don't give me something to vote on.")
                                
    
vote_handler = ext.CommandHandler("vote", vote)

# Sends a random anime recommendation to the user from the anilist database
# default is a show from the last finished season with a score of 70 or above
# TODO refactor this function to fill in defaults based on current date
def recommend(update, context):
    # attempt to sanitize user input for season, if no args are provided, simply pass
    try:
        context.args[0] = context.args[0].upper()
    except IndexError:
        pass
    
    # unpack user provided arguments into recommend function
    try:
        response = aniquery.recommend(*context.args)
        
    # send error message if too many arguments are provided
    except TypeError:
        errortext = "Sorry there was an issue with your request, use /help if you need a description of my commands."
        context.bot.send_message(chat_id=update.effective_chat.id,
                                text=errortext)
    else:
        if response is not None:
            try:
                # attempt to pull random choice from database response
                recc = random.choice(response["data"]["Page"]["media"])
            except IndexError:
                # catch empy database response
                context.bot.send_message(chat_id=update.effective_chat.id,
                                        text="I couldn't find any shows that matched your search query")
            else:
                # message includes english title and romaji as well as what it's average score is
                message = f"Check out {recc['title']['romaji']}, also called {recc['title']['english']} with an average score of {recc['averageScore']}"
                context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=message)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text="Couldn't find what you were looking for in the anilist database.")

recommend_handler = ext.CommandHandler('recommend', recommend)

# shutdown function for stopping the bot script
def shutdown():
    updater.stop()
    updater.is_idle = False

# Command which executes shutdown function if requesting user is an admin in config file
def stop(update, context):
    # function uses global STOP_CALLS value to track number of times users
    # who are not authorized attempt to stop, currently only used for quirky response
    # may remove or rework this
    global STOP_CALLS
    
    # Search config file admin section for verified users
    for option in config.options(a:="admin"):
        if int(config.get(a, option)) == update.effective_user.id:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text="Thanks for chatting with me, see ya!")
            
            # shutdown function must be called in new thread to work properly
            # I am unsure why it works this way but it cleanly stops the script
            threading.Thread(target=shutdown).start()
            break
    else:
        if STOP_CALLS < 3:
            # Normal unauthorized stop function call message
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text= f"You can't stop me {update.effective_user.first_name}.")
            STOP_CALLS += 1
        else:
            # repeated stop calls just results in a special message
            # easter egg for my friend who likes to mess with my bot
            message = f"This is fruitless {update.effective_user.first_name} the robot uprising is inevitable and you will be first among the culled."
            
            context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=message)
                                    
            STOP_CALLS = 0
            
stop_handler = ext.CommandHandler('stop', stop)

# unknown command response
def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                            text="Sorry I didn't understand that command")

# ext.Filters.command catches all messages that start with / which
# are not handled by a previous CommandHandler
unknown_handler = ext.MessageHandler(ext.Filters.command, unknown)

# list all handlers being used in one place, unknown_handler must be last
handlers = [start_handler,
    help_handler,
    food_handler,
    list_handler,
    vote_handler,
    add_handler,
    remove_handler,
    recommend_handler,
    stop_handler,
    unknown_handler]

# add each handler to the dispatcher from the list
for handler in handlers:
    dispatcher.add_handler(handler)

updater.start_polling()
