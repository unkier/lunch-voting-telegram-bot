#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Dmitry Shapovalov <dmitry@0fe.ru>
# @Date:   06-07-2017
# 
# lunch voting telegram bot

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from datetime import datetime, timedelta, time, date
import logging
import re
import os

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

DELAY_RE = re.compile("^\s*\+\s*(\d+)")

vote_start_time = None
vote_in_progress = False
voters = {}

# secret token from BotFather
SECRET_TOKEN = os.getenv('LUNCH_VOTING_BOT_SECRET_TOKEN', "incorrect_secret_token")

# chat id
CHAT_ID = int(os.getenv('LUNCH_VOTING_BOT_CHAT_ID', "incorrect_chat_id"))

VOTE_BEGIN_TIME = (8,00)
LUNCH_HOUR_TIME = (12,00)
LUNCH_REMIND = 30 #minutes before lunch
LUNCH_WEEK_DAYS = (0, 1, 2, 3, 4)
MAX_DELAY = 30

VOTE_START_MSG = "Обед в %d:%d\nесть время подумать" % (LUNCH_HOUR_TIME[0],LUNCH_HOUR_TIME[1])
VOTE_REMIND_MSG = "Обед через %d минут" % LUNCH_REMIND
VOTE_STOP_MSG = "Кто не успел, тот опоздал...\nИтог такой:\n"

LUNCH_REMIND_TIME = (datetime.combine(date.today(),time(hour=LUNCH_HOUR_TIME[0], minute=LUNCH_HOUR_TIME[1]))-timedelta(minutes=LUNCH_REMIND)).time()
VOTE_START_TIME = time(hour=VOTE_BEGIN_TIME[0], minute=VOTE_BEGIN_TIME[1])
VOTE_STOP_TIME = time(hour=LUNCH_HOUR_TIME[0], minute=LUNCH_HOUR_TIME[1])

class Voter:
    def __init__(self, decision=False, delay=0, name="Anon"):
        self.decision = decision
        self.delay = delay
        self.name = name

def vote(voter,decision,delay=0):
    if voter.id in voters:
        voters[voter.id].decision = decision
        voters[voter.id].delay = delay
    else:
        voters[voter.id] = Voter(decision=decision, delay=delay, name="%s %s" % (voter.first_name,voter.last_name))

def listen_all(bot, update):
    if not vote_in_progress:
        return
    if update.message.chat.id != CHAT_ID:
        return

    if update.message.text.strip() == "-":
        vote(update.message.from_user,False)
    elif update.message.text.strip() == "+":
        vote(update.message.from_user,True)
    else:
        result = DELAY_RE.match(update.message.text)
        if result:
            delay = result.group(1)
            vote(update.message.from_user,True,int(delay))

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def vote_start(bot, job):
    global vote_in_progress
    global vote_start_time
    vote_in_progress = True
    bot.send_message(chat_id=CHAT_ID,text=VOTE_START_MSG)

def vote_remind(bot, job):
    bot.send_message(chat_id=CHAT_ID,text=VOTE_REMIND_MSG)

def vote_end(bot, job):
    global vote_in_progress
    vote_in_progress = False
    voter_message = ""
    for voter in voters.values():
        if voter.decision:
            if voter.delay > 0:
                voter_message += "%s задержится на %d минут\n" % (voter.name, voter.delay)
            else:
                voter_message += "%s пойдет\n" % voter.name
        else:
            voter_message += "%s не пойдет\n" % voter.name
    bot.send_message(chat_id=CHAT_ID,text=VOTE_STOP_MSG+voter_message)

def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(SECRET_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # listen all    
    dp.add_handler(MessageHandler(Filters.text, listen_all))

    # log all errors
    dp.add_error_handler(error)

    updater.job_queue.run_daily(vote_start, VOTE_START_TIME, days=LUNCH_WEEK_DAYS)
    updater.job_queue.run_daily(vote_remind, LUNCH_REMIND_TIME, days=LUNCH_WEEK_DAYS)
    updater.job_queue.run_daily(vote_end, VOTE_STOP_TIME, days=LUNCH_WEEK_DAYS)

    # if VOTE_START_TIME is passed, start vote now
    if datetime.now().time() > VOTE_START_TIME and datetime.now().time() < VOTE_STOP_TIME:
        updater.job_queue.run_once(vote_start, timedelta(minutes=1))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
