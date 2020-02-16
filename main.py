#!/usr/bin/python
# -*- coding: utf-8 -*-
# gcloud beta functions deploy webhook --runtime python37 --trigger-http

import os
import telegram
import logging
#import requests
import datetime
import threading
import json
#from telegram.ext.dispatcher import run_async  # TO DO
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, \
    Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import gspread
from oauth2client.service_account import ServiceAccountCredentials

 
###############################################################################


#To deploy, run command : gcloud functions deploy webhook-EU-Server --entry-point webhook --region europe-west1 --runtime python37 --trigger-http

#To set webhook : https://api.telegram.org/bot{my_bot_token}/setWebhook?url={url_to_send_updates_to}
#Expected response from server : {"ok":true,"result":true,"description":"Webhook was set"}

#Emoji list : http://www.unicode.org/emoji/charts/full-emoji-list.html#1f604 | using this format(change last 5 char) - u'\U0001f604'

TOKEN=os.environ.get('TOKEN')
bot = telegram.Bot(token=TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0)


###################### Set Global Parameters ##################################

class Cookhouse:
    def __init__(self,num):
        # {'NM':{"Lunch": {"Monday":"", :"Tuesday":"","Wednesday":"","Thursday":"","Friday":""} },"Breakfast":....
        self.num=num

        
        food_menu={}
        prefs=["NM","M","V"]
        self.days=["<b>Monday</b>","<b>Tuesday</b>","<b>Wednesday</b>","<b>Thursday</b>","<b>Friday</b>"]

        # Configure dictionary
        for pref in prefs:
            food_menu[pref]={"Lunch":{},"Breakfast":{},"Dinner":{}}
            for meal in food_menu[pref].keys():
                for day in self.days:
                    food_menu[pref][meal][day]=""
                    
        self.food_menu=food_menu

        self.last_update_date=None
        self.menu_date=None

    def get_lunch_menu(self,typ):
        if typ=="NM":
            return self.food_menu["NM"]["Lunch"]
        elif typ=="M":
            return self.food_menu["M"]["Lunch"]
        elif typ=="V":
            return self.food_menu["V"]["Lunch"]

    def set_lunch_menu(self):
        global menu_ws
        num=self.num
        
        self.last_update_date=menu_ws[num].acell('A3').value
        self.menu_date=menu_ws[num].acell('A2').value

        cell_list=menu_ws[num].range('C3:S3')
        pic_list=menu_ws[num].range('C4:S4')
          
        i = 0
        for key in self.days:
            self.food_menu["NM"]["Lunch"][key] = [cell_list[i].value,pic_list[i].value]
            self.food_menu["M"]["Lunch"][key] = [cell_list[i+6].value,pic_list[i+6].value]
            self.food_menu["V"]["Lunch"][key] = [cell_list[i+12].value,pic_list[i+12].value]
            i += 1

    def get_breakfast_menu(self,typ):
        if typ=="NM":
            return self.food_menu["NM"]["Breakfast"]
        elif typ=="M":
            return self.food_menu["M"]["Breakfast"]
        elif typ=="V":
            return self.food_menu["V"]["Breakfast"]

    def set_breakfast_menu(self):
        global menu_ws
        num=self.num
        
        self.last_update_date=menu_ws[num].acell('A3').value
        self.menu_date=menu_ws[num].acell('A2').value

        cell_list=menu_ws[num].range('C13:S13')
        pic_list=menu_ws[num].range('C14:S14')
          
        i = 0
        for key in self.days:
            self.food_menu["NM"]["Breakfast"][key] = [cell_list[i].value,pic_list[i].value]
            self.food_menu["M"]["Breakfast"][key] = [cell_list[i+6].value,pic_list[i+6].value]
            self.food_menu["V"]["Breakfast"][key] = [cell_list[i+12].value,pic_list[i+12].value]
            i += 1

    def get_dinner_menu(self,typ):
        if typ=="NM":
            return self.food_menu["NM"]["Dinner"]
        elif typ=="M":
            return self.food_menu["M"]["Dinner"]
        elif typ=="V":
            return self.food_menu["V"]["Dinner"]

    def set_dinner_menu(self):
        global menu_ws
        num=self.num
        
        self.last_update_date=menu_ws[num].acell('A3').value
        self.menu_date=menu_ws[num].acell('A2').value

        cell_list=menu_ws[num].range('C23:S23')
        pic_list=menu_ws[num].range('C24:S24')
          
        i = 0
        for key in self.days:
            self.food_menu["NM"]["Dinner"][key] = [cell_list[i].value,pic_list[i].value]
            self.food_menu["M"]["Dinner"][key] = [cell_list[i+6].value,pic_list[i+6].value]
            self.food_menu["V"]["Dinner"][key] = [cell_list[i+12].value,pic_list[i+12].value]
            i += 1

qs_menu={}

greeting="Enjoy your meal! " + u'\U0001f60b' + " How else can i help?"

num_cookhouse=1

scope = ['https://spreadsheets.google.com/feeds',
     'https://www.googleapis.com/auth/drive']
credentials = \
ServiceAccountCredentials.from_json_keyfile_name('My First Project-764ab02d082d.json'
            , scope)




############# Initalise program ###############################

def login_gsheets():
    global qs_menu,menu_ws
    global scope,credentials,gc,chatlog_ws


    # Init google credentials
    gc = gspread.authorize(credentials)
    menu_ws=[]
    for i in range(num_cookhouse):
        menu_ws+=[gc.open('Telegram bot').get_worksheet(i)]
    chatlog_ws= gc.open('Telegram bot').get_worksheet(num_cookhouse)

    
    # Update menu and qs list

    global cookhouses
    cookhouses=[]
    for i in range(num_cookhouse):
        cookhouses+=[Cookhouse(i)]
        cookhouses[i].set_lunch_menu()
        cookhouses[i].set_breakfast_menu()
        cookhouses[i].set_dinner_menu()
    # Blk 826
   
    update_qs_menu(qs_menu)

    update_chatlog_index()

    logging.info("Refreshing Gsheets")

    #Refresh google sheets session every 1800s
    threading.Timer(1800, login_gsheets).start()



def update_chatlog_index():
    global chatlog_ws
    cell_list = chatlog_ws.range('A2:A9999')
    for i in range(2, 99999):
        if cell_list[i - 2].value == '':
            index = i
            chatlog_ws.update_acell('K1', index)
            break



#######################################################################
        

################## Button callback functions ##########################

def menu_callback(bot,update):
    query = update.callback_query
    option=int(query.data)
    bot.answer_callback_query(update.callback_query.id)

    # 0 - 426
    if option==1:
        menu_lunch(bot,query,"NM",0)
    elif option==2:
        menu_lunch(bot,query,"M",0)
    elif option==3:
        menu_lunch(bot,query,"V",0)
        
    elif option==4:
        survey_url="https://form.gov.sg/#!/5c89d12177ef5300174c21a8"
        #survey_url="https://forms.gle/zvXj7RdPLMEdp7Ds6"
        chat_id = query.message.chat_id
        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
        survey_greeting="Please kindly fill up the survey form for us " + u'\U0001f604'
        bot.send_message(chat_id=chat_id, text=survey_greeting+"\n"+survey_url)
        
    elif option==5:
        menu_breakfast(bot,query,"NM",0)
    elif option==6:
        menu_breakfast(bot,query,"M",0)
    elif option==7:
        menu_breakfast(bot,query,"V",0)

    elif option==8:
        menu_dinner(bot,query,"NM",0)
    elif option==9:
        menu_dinner(bot,query,"M",0)
    elif option==10:
        menu_dinner(bot,query,"V",0)

        

    logging.info(str(query.message.chat_id)+" "+str(query.message.chat.first_name)+" has selected Option "+str(option))
    

     
def survey_callback(bot,update):
    bot.answer_callback_query(update.callback_query.id)
    #survey_url="https://form.gov.sg/#!/5c89d12177ef5300174c21a8"
    survey_url="https://forms.gle/TYVANzHLgAq2fnaR6"
    query = update.callback_query
    chat_id = query.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    
    survey_greeting="Please kindly fill up the survey form for us" + u'\U0001f604'
    
    bot.send_message(chat_id=chat_id, text=survey_greeting)
    bot.send_message(chat_id=chat_id, text=survey_url)
    logging.info("Option " + query.data + " has been selected" )
    
    
########################################################################


################ Update/Retrieve from Gsheets ##########################

def update_qs_menu(menu):
    qs_list=chatlog_ws.range('G10:G18')
    ans_list=chatlog_ws.range('H10:H18')
    i=0
    for qs in qs_list:
        menu[qs.value]=ans_list[i].value
        i+=1
    logging.info(qs_menu)
        
        
def update_gsheet(name, chat_id, msg):
    global chatlog_ws
    timestamp = str(datetime.datetime.now())
    index = int(chatlog_ws.acell('K1').value)
    chatlog_ws.update_acell('A' + str(index), timestamp)
    chatlog_ws.update_acell('B' + str(index), chat_id)
    chatlog_ws.update_acell('C' + str(index), name)
    chatlog_ws.update_acell('D' + str(index), msg)
    chatlog_ws.update_acell('K1', index + 1)

    
########################################################################


def dog(bot, update):
    import requests
    contents = requests.get('https://random.dog/woof.json').json()
    url = contents['url']
    chat_id = update.message.chat_id
    bot.send_photo(chat_id=chat_id, photo=url,caption="Congrats on finding an easter egg!\nHere's a cute doggie for you, woof woof!",)
    

def update(bot, update):
    chat_id = update.message.chat_id
    sent=bot.send_message(chat_id=chat_id, text='Updating...')
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    try:        
        login_gsheets()
        bot.edit_message_text(chat_id=chat_id,message_id=sent.message_id, text='Successfully Updated!')
    except Exception as e:
        logging.error(e)
        bot.edit_message_text(chat_id=chat_id,message_id=update.message.message_id, text='Update failed,please contact sys admin')


def ranks(bot, update):
    chat_id = update.message.chat_id
    rank_url = 'https://mustsharenews.com/wp-content/uploads/2018/04/' \
        + 'army-ranks-infographics-final.jpg'
    bot.send_photo(chat_id=chat_id, photo=rank_url)
    

    
def menu_lunch(bot, update, typ, num):

    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    menu_typ_text={"NM":"Non-Muslim","M":"Muslim","V":"Veg"}

    menu=cookhouses[num].get_lunch_menu(typ)
    cookhouse_name={0:"BLK 826"}
    
    dtText=cookhouse_name[num]+ " Cookhouse : " + menu_typ_text[typ]+" Lunch Menu for the week of <i>" + cookhouses[num].menu_date + "</i> \nupdated on "+ cookhouses[num].last_update_date

            
    bot.send_message(chat_id=chat_id, text=dtText,parse_mode=telegram.ParseMode.HTML)
       
    for (day, food) in menu.items():
        if food[1]!="":
            try:
                bot.send_photo(chat_id=chat_id,photo=food[1],caption=day +
                               ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
            except:
                bot.send_message(chat_id=chat_id, text=day + ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=chat_id, text=day + ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
    
    bot.send_message(chat_id=chat_id, text=greeting)
    start(bot, update)


def menu_breakfast(bot, update, typ, num):

    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    menu_typ_text={"NM":"Non-Muslim","M":"Muslim","V":"Veg"}

    menu=cookhouses[num].get_breakfast_menu(typ)
    cookhouse_name={0:"BLK 826"}
    
    dtText=cookhouse_name[num]+ " Cookhouse : " + menu_typ_text[typ]+" Breakfast Menu for the week of <i>" + cookhouses[num].menu_date + "</i> \nupdated on "+ cookhouses[num].last_update_date

            
    bot.send_message(chat_id=chat_id, text=dtText,parse_mode=telegram.ParseMode.HTML)
       
    for (day, food) in menu.items():
        if food[1]!="":
            try:
                bot.send_photo(chat_id=chat_id,photo=food[1],caption=day +
                               ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
            except:
                bot.send_message(chat_id=chat_id, text=day + ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=chat_id, text=day + ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
    
    bot.send_message(chat_id=chat_id, text=greeting)
    start(bot, update)


def menu_dinner(bot, update, typ, num):

    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    menu_typ_text={"NM":"Non-Muslim","M":"Muslim","V":"Veg"}

    menu=cookhouses[num].get_dinner_menu(typ)
    cookhouse_name={0:"BLK 826"}
    
    dtText=cookhouse_name[num]+ " Cookhouse : " + menu_typ_text[typ]+" Dinner Menu for the week of <i>" + cookhouses[num].menu_date + "</i> \nupdated on "+ cookhouses[num].last_update_date

            
    bot.send_message(chat_id=chat_id, text=dtText,parse_mode=telegram.ParseMode.HTML)
       
    for (day, food) in menu.items():
        if food[1]!="":
            try:
                bot.send_photo(chat_id=chat_id,photo=food[1],caption=day +
                               ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
            except:
                bot.send_message(chat_id=chat_id, text=day + ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=chat_id, text=day + ': ' + food[0],parse_mode=telegram.ParseMode.HTML)
    
    bot.send_message(chat_id=chat_id, text=greeting)
    start(bot, update)


def menu_temp(bot, update):
    update = update.callback_query
    bot.answer_callback_query(update.id)
    
    chat_id = update.message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    
    bot.send_message(chat_id=chat_id, text="Sorry, i am still undergoing training. Stay tune for this feature!")
    start(bot, update)

    
def start(bot, update):
    keyboard = [InlineKeyboardButton('Breakfast', callback_data='Breakfast'),
                InlineKeyboardButton('Lunch', callback_data='Lunch'),
                InlineKeyboardButton('Dinner', callback_data='Dinner')],
             

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Which meal are you looking for? ',
                              reply_markup=reply_markup)

    try:
        chat_id = update.message.chat_id
        message_id=update.message.message_id
        bot.delete_message(chat_id=chat_id,message_id=message_id)
    except:
        pass
        
    return


def cookhouse_menu(bot, update):
    update = update.callback_query
    bot.answer_callback_query(update.id)
    data=update.data

    if data=="Lunch":
        keyboard = [[InlineKeyboardButton('Non Muslim', callback_data='1'),
                    InlineKeyboardButton('Muslim', callback_data='2')],
                    [InlineKeyboardButton('Vegetarian', callback_data='3'),
                     InlineKeyboardButton('Survey', callback_data='4')]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Blk 826 Cookhouse, Which " + data +" menu are you looking for?",
                                  reply_markup=reply_markup)

    elif data=="Breakfast":
        keyboard = [[InlineKeyboardButton('Non Muslim', callback_data='5'),
                    InlineKeyboardButton('Muslim', callback_data='6')],
                    [InlineKeyboardButton('Vegetarian', callback_data='7'),
                     InlineKeyboardButton('Survey', callback_data='4')]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Blk 826 Cookhouse, Which " + data +" menu are you looking for?",
                                  reply_markup=reply_markup)

    elif data=="Dinner":
        keyboard = [[InlineKeyboardButton('Non Muslim', callback_data='8'),
                    InlineKeyboardButton('Muslim', callback_data='9')],
                    [InlineKeyboardButton('Vegetarian', callback_data='10'),
                     InlineKeyboardButton('Survey', callback_data='4')]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Blk 826 Cookhouse, Which " + data +" menu are you looking for?",
                                  reply_markup=reply_markup)
 
    try:
        chat_id = update.message.chat_id
        message_id=update.message.message_id
        bot.delete_message(chat_id=chat_id,message_id=message_id)
    except:
        pass
        
    return
 

def info(bot, update):
    chat_id = update.message.chat_id
    txt = \
        '''HQ Supply has <b>8</b> branches
MPB, GSB, GLSB, SDB,
SCMB, EMB, PMB, RMB
''' \
        + '\n<b>CSPO</b>: COL Chang Pin Chuan | <b>DY</b>: LTC Soh Chih Ping' \
        + '\n<b>FSM</b>: SWO Lim Hock Heng | <b>CSM</b>: 2WO Albert Chew'
    bot.send_message(chat_id=chat_id, text=txt,
                     parse_mode=telegram.ParseMode.HTML)



def parse(bot, update):
    global qs_menu
    chat_id = update.message.chat_id
    name = update.message.chat.first_name
    msg_raw = update.message.text
    msg_parsed = msg_raw.lower().replace(' ', '')

    if not name and not msg_parsed:
        return
    elif 'moose' in name and 'celess' in msg_parsed:
        bot.sendMessage(chat_id=chat_id, text='Go talk to her!')
    else:
        if 'sexy' in msg_parsed:
            # https://lh3.google.com/u/0/d/<file_id>
            mus_url = \
                'https://lh3.googleusercontent.com/DIAC_9vOagu7ECamQ0puuSMyeaeHaKt5zEaMuOqowxQ08hgfedIraCShBmWbJ2yG_ePvlkyhaBqWZ7IyDNnnsuECRahfZtwFf_tCUx45P7col5RRSB4OmgHSW1KlZA7pFTsrQdP9NVKhLpTt62NK8H1Hn_8dwU3WKNABagjESqHRm8QaBte-RKkGaPlAZC8uNfl2v7jW0yLdCZCYzds9OqT1gc4dquxNEZcf6HH1erCVHqeYi5KUsLZx-CERi6peepZYAvehEPxkPfB-46tq8rxYrIlbGydBl18eL12sVG9Z_d7Om3SJQCk86GQtOoSi6OLmiC_usSQduB7CiIdFok6zScaI_1irPxy21c3fO-GikIr9vWDPi4JpLJsEko4RVFDvAEBXmBkeFDr3wFnprG8i1gbCBBzr9aVq36O7k96FJV4iK9rp2qCVrr5q4mCTtIHDL7NwiPfFqB2hbMytRmXLATsMfyo6KNevM0P03JpOuHqWtpLkR-6ettCdtm6KLjX47_-fJP-al7XDRO2CsjGZVqhi2G8olh5iaL7GP8eF7VDEuC-IYTomAyScoBnxr0awlv2eU0oYD1watrpaXCssXknQ5DRRpn_b'
            bot.send_photo(chat_id=chat_id, photo=mus_url)
        elif 'whoisdy' in msg_parsed:
            dy_url="https://i.imgur.com/BLbbW5a.jpg"
            bot.send_photo(chat_id=chat_id, photo=dy_url,caption="Congrats you found an easter egg!")
        else:
            # Look for question in qs_menu dict
            for qs in qs_menu.keys():
                if qs in msg_parsed:
                    bot.sendMessage(chat_id=chat_id,text=qs_menu[qs])
                    break
            else:
                bot.sendMessage(chat_id=chat_id, text=msg_raw)

    update_gsheet(name, chat_id, msg_raw)


def bus(bot,update):
    chat_id = update.message.chat_id
    text=update.message.text
    params=text.split(" ")[1]
    if len(params)<5:
        url="https://busrouter.sg/#/services/" + params
    else:
        url="https://busrouter.sg/#/stops/" + params
    bot.sendMessage(chat_id=chat_id, text=url)

def mrt(bot,update):
    chat_id = update.message.chat_id
    url="https://railrouter.sg/"
    bot.sendMessage(chat_id=chat_id, text=url)

def taxi(bot,update):
    chat_id = update.message.chat_id
    url="https://taxirouter.sg/"
    bot.sendMessage(chat_id=chat_id, text=url)


def setup():

    global dispatcher

    # ---Register handlers here---

    # Commands Handlers
    dispatcher.add_handler(CommandHandler('start', start))
    
    dispatcher.add_handler(CommandHandler('doggy', dog))
    dispatcher.add_handler(CommandHandler('bus', bus))
    dispatcher.add_handler(CommandHandler('mrt', mrt))
    dispatcher.add_handler(CommandHandler('taxi', taxi))
    
    dispatcher.add_handler(CommandHandler('menu', start))
    #dispatcher.add_handler(CommandHandler('info', info))
    dispatcher.add_handler(CommandHandler('ranks', ranks))
    dispatcher.add_handler(CommandHandler('update', update)) # Force update from gsheets

    # Message Handlers
    dispatcher.add_handler(MessageHandler(Filters.text, parse)) # To process text

    # Button Handlers
    dispatcher.add_handler(CallbackQueryHandler(cookhouse_menu, pattern='Breakfast')) # breakfast Button
    dispatcher.add_handler(CallbackQueryHandler(cookhouse_menu, pattern='Lunch')) # lunch Button
    dispatcher.add_handler(CallbackQueryHandler(cookhouse_menu, pattern='Dinner')) # dinner Button

    # Lunch
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='1')) # NM Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='2')) # M Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='3')) # V Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='4'))# Survey Button

    # Breakfast
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='5')) # NM Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='6')) # M Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='7')) # V Button

    # Dinner
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='8')) # NM Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='9')) # M Button
    dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='10')) # V Button

    # dispatcher.add_error_handler(error)

    return dispatcher
        
    

##########################################################################

# Set up
login_gsheets()
setup()


##########################################################################

# Webhook

def webhook(request):
    global dispatcher

    # Manually get updates and pass to dispatcher
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    logging.info(update)
    dispatcher.process_update(update)

    return




            
