from stmpy import Machine, Driver
from os import system
from gtts import gTTS
from pydub import AudioSegment
import logging
import pyaudio
import wave

debug_level = logging.DEBUG
logger = logging.getLogger('stmpy')
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class Speaker:
    def __init__(self):
        self.audio_file_name = "string"

    def speak(self, string):
        # TTS
        tts = gTTS(string, lang="en")
        tts.save(self.audio_file_name+'.mp3')
        # Convert .mp3 to .wav using ffmpeg
        sound = AudioSegment.from_mp3(self.audio_file_name+'.mp3')
        sound.export(self.audio_file_name+'.wav', format="wav")
        
        # Play the .wav file using PyAudio
        filename = self.audio_file_name+'.wav'
        # Set chunk size of 1024 samples per data frame
        chunk = 1024  
        # Open the sound file 
        wf = wave.open(filename, 'rb')
        # Create an interface to PortAudio
        p = pyaudio.PyAudio()
        # Open a .Stream object to write the WAV file to
        # 'output = True' indicates that the sound will be played rather than recorded
        stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                        channels = wf.getnchannels(),
                        rate = wf.getframerate(),
                        output = True)
        # Read data in chunks
        data = wf.readframes(chunk)
        # Play the sound by writing the audio data to the stream
        while data != b'':
            stream.write(data)
            data = wf.readframes(chunk)
        # Close and terminate the stream
        stream.close()
        p.terminate()

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
