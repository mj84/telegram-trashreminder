#!/usr/bin/env python3
from ics import Calendar
import datetime
from operator import itemgetter
import logging
from telegram.ext import Updater, CommandHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Filename to read dates from
filename = "ICS FILENAME HERE"
# Daily reminder time
remind_hours = 18
remind_minutes = 30

# Initialize datestamp from tomorrow
tomorrow = datetime.date.today() + datetime.timedelta(days=1)
def read_events_from_file(filename):
    try:
        with open(filename, 'r') as file:
            data = file.read()
        c = Calendar(data)
        #print(len(c.events))
        events = []
        for event in c.events:
            event_date = event.begin.date()
            # Remove an unwanted substring
            event_description = event.name.replace('HIS ', '')
            if event_date >= tomorrow:
                events.append((event_date, event_description))
            else:
                pass
                #print('Dropping event %s on %s' % (event_description, event_date))
        # Sort events by date ascending
        events_sorted = sorted(events, key=itemgetter(0))
        return events_sorted
    except Exception as e:
        logger.warning('Exception encountered: ' % e)
        pass

def alarm(context):
    job = context.job
    chat_id = job.context.chat_data['chat_id']
    events = job.context.chat_data['events']
    context.bot.send_message(chat_id, text='Tomorrow is trashday for %s' % job.name)
    # This is a weird way to remove the event of the current job:
    # Walk over the list of events, and remove the first matching the current job name
    event_index = 0
    for event in events:
        if event[1] == job.name:
            break
        event_index += 1
    job.context.chat_data['events'].pop(event_index)
    logger.info('Sent reminder for %s to chat %s' % (job.name, chat_id))

def upcoming(update, context):
    upcoming_events = context.chat_data['events'][:5]
    update.message.reply_text('These are the next %s trashdays:' % len(upcoming_events))
    reply = ''
    for event in upcoming_events:
        reply += '%s: %s\n' % event
    update.message.reply_text(reply)

def start(update, context):
    username = update._effective_user.username
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    context.chat_data['username'] = username
    logger.info('/start called by user %s' % username)
    update.message.reply_text('''Hi!
I will remind you for upcoming trashdays every day at %s:%s.
Please use the following commands for this bot:
/upcoming Show the next upcoming trashdays
''' % (remind_hours, remind_minutes))
    chat_id = update.message.chat_id
    events = read_events_from_file(filename)
    context.chat_data['events'] = events
    context.chat_data['chat_id'] = chat_id
    # Schedule a job for every event found in ics file
    for event in events:
        event_date, event_description = event
        remind_datetime = datetime.datetime.combine(event_date, datetime.datetime.min.time()) - datetime.timedelta(days=1) + datetime.timedelta(hours=remind_hours) + datetime.timedelta(minutes=remind_minutes)
        remind_datetime_local = remind_datetime.replace(tzinfo=datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)
        logger.info('Scheduled job due at %s with description %s for user %s' % (remind_datetime_local, event_description, username))
        new_job = context.job_queue.run_once(callback=alarm, when=remind_datetime_local, context=context, name=event_description)
    try:
        pass
    except Exception as e:
        update.message.reply_text('''I had a problem creating your reminder.
        Please contact my master.
        ''')


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    updater = Updater("TELEGRAM BOT TOKEN HERE", use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("upcoming", upcoming))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
