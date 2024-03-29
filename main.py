from telegram import Update
from telegram.ext import (Application,CommandHandler,ContextTypes,CallbackContext ,PicklePersistence, MessageHandler,filters)
from dotenv import dotenv_values
from subprocess import check_output
from scrapper import Scrapper
import pickle
import pendulum
import os

TELEGRAM_TOKEN = dotenv_values('.env')["TELEGRAM_TOKEN"]
DATA_DIRECTORY = os.path.expanduser("./data/")

class ScrapperApp:
    async def _scheduledUpdate(self,context:ContextTypes.DEFAULT_TYPE)->None:
        job = context.job
        current_date= str(pendulum.now().date())
        self.scrapper.updateSavedProd(current_date)
        update_str = self.scrapper.updateString(current_date)
        if update_str:
            await context.bot.send_message(job.chat_id,update_str,parse_mode="HTML")
        else:
            print(f"There was no update {pendulum.now().format('dddd DD MM YYYY')}")

    async def _getIP(self,update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
        ip_addr = check_output("curl -s ifconfig.me" ,shell=True)
        ip_addr = ip_addr.decode("utf-8")
        await update.message.reply_text(ip_addr)

    def _isSubscribed(self,update:Update, context:ContextTypes.DEFAULT_TYPE)->bool:
        chat_id = str(update.message.chat_id)
        chat_jobs = context.job_queue.get_jobs_by_name(chat_id)
        return len(chat_jobs)


    async def _subscribe(self,update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
        if self._isSubscribed(update=update,context=context):
            await update.message.reply_text("You're already subscribed")
            return 
        _chat_id = str(update.message.chat_id)
        self.subscriptions +=[_chat_id]
        print(self.subscriptions)
        with open(f"{DATA_DIRECTORY}subscriptions.pckl","+wb") as subs_pickle_file:
            pickle.dump(self.subscriptions,subs_pickle_file)
        context.job_queue.run_repeating(self._scheduledUpdate,first=1,interval=3600,name=_chat_id,chat_id=_chat_id)    
        await update.message.reply_text("Succesfully subscribed")

    async def _nextUpdate(self,update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
        _chat_id = str(update.message.chat_id)
        if self._isSubscribed(update,context):
            next_job= context.job_queue.get_jobs_by_name(_chat_id)[0]
            _time_delta = next_job.next_t - pendulum.now()
            await update.message.reply_text(f'Next update scheduled in {_time_delta.in_minutes()} minutes')
            return
        await update.message.reply_text("Not subscribed")

    async def _defaultHandler(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
        #TODO
        #check if is a valid product url 
        #if so add as product
        #add a reply for feedback
        pass 


    async def _addProduct(self,update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
        _message = update.message.text
        prodURL = _message.split()[1]
        add_result = self.scrapper.addProd(prodURL)
        await update.message.reply_text("Product Added succesfully" if add_result else "Failed to add")
        return
    
    def _initTelegramApp(self):
        _persistence = PicklePersistence(filepath=f"{DATA_DIRECTORY}persistence.pckl")
        self.telegramApp = Application.builder().token(TELEGRAM_TOKEN).persistence(_persistence).build()
        self.telegramApp.add_handler(CommandHandler("get_ip", self._getIP))
        self.telegramApp.add_handler(CommandHandler("next_update", self._nextUpdate))
        self.telegramApp.add_handler(CommandHandler("subscribe", self._subscribe))
        self.telegramApp.add_handler(CommandHandler("add", self._addProduct))
        self.telegramApp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._defaultHandler))
        self._restoreSubscriptions()
        self.telegramApp.run_polling()
        return

    def _initScrapper(self):
        self.scrapper = Scrapper(DATA_DIRECTORY)
        return
        
    def _getSubscriptions(self,data_directory)->None:
        if not os.path.exists(f"{data_directory}subscriptions.pckl"):    
            self.subscriptions = []
            return
        with open(f"{data_directory}subscriptions.pckl","rb") as subs_pickle_file:
            self.subscriptions = pickle.load(subs_pickle_file)    

    def _restoreSubscriptions(self)->None:
        self._getSubscriptions(DATA_DIRECTORY)
        for _chat_id in self.subscriptions:
            self.telegramApp.job_queue.run_repeating(self._scheduledUpdate,first=1,interval=3600,name=_chat_id,chat_id=_chat_id)
        

        

    def __init__(self):    
        self._initScrapper()
        
        self._initTelegramApp()


        

def main():
    myApp = ScrapperApp()

if __name__ == '__main__':
    main()
