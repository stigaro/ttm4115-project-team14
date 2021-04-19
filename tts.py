from stmpy import Machine, Driver
from os import system
import pyttsx3
import logging
from gtts import gTTS
from playsound import playsound

debug_level = logging.DEBUG
logger = logging.getLogger('stmpy')
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class Speaker:
    def speak(self, string):
        tts = gTTS(string, lang="en")
        tts.save('string.mp3')
        playsound("string.mp3")
        #engine = pyttsx3.init()
        #engine.say(string)
        #engine.runAndWait()
        #system('say {}'.format(string))

speaker = Speaker()

t0 = {'source': 'initial', 'target': 'ready'}
t1 = {'trigger': 'speak', 'source': 'ready', 'target': 'speaking'}
t2 = {'trigger': 'done', 'source': 'speaking', 'target': 'ready'}

s1 = {'name': 'speaking', 'do': 'speak(*)', 'speak': 'defer'}

stm = Machine(name='stm', transitions=[t0, t1, t2], states=[s1], obj=speaker)
speaker.stm = stm

driver = Driver()
driver.add_machine(stm)
driver.start()

driver.send('speak', 'stm', args=['My first sentence.'])
driver.send('speak', 'stm', args=['My second sentence.'])
driver.send('speak', 'stm', args=['My third sentence.'])
driver.send('speak', 'stm', args=['My fourth sentence.'])

driver.wait_until_finished()
