import speech_recognition as sr
from stmpy import Machine, Driver


class Recognizer:
    def __init__(self, audio_file_name: str):
        self.latest_recognition = ""
        self.speech_converter = sr.Recognizer()
        self.audio_file_name = audio_file_name
        self.stm = None

    def recognize(self):
        # noinspection PyBroadException
        try:
            print("[RECOGNIZE]: Recognizing audio")

            with sr.AudioFile('output.wav') as audio_source:
                audio = self.speech_converter.listen(audio_source)

            self.latest_recognition = "[MESSAGE]:" + self.speech_converter.recognize_google(audio)

        except FileNotFoundError:
            print('[RECOGNIZE]: Was unable to recognize')
            self.latest_recognition = "[ERROR]:" + "Could not load audio file"
        except Exception:
            print('[RECOGNIZE]: Was unable to recognize')
            self.latest_recognition = "[ERROR]:" + "General internal error"

        # Standardize to lowercase and return that we are done
        self.latest_recognition = self.latest_recognition.lower()
        self.stm.send('done')

    def report(self):
        # TODO: Needs to send message, currently only prints latest recognition
        print("Latest recognition => " + self.latest_recognition.lower())
        pass


if __name__ == "__main__":
    recognizer = Recognizer('output.wav')

    t_i0 = {'source': 'initial', 'target': 'ready'}
    t_01 = {'trigger': 'recognize', 'source': 'ready', 'target': 'recognizing'}
    t_10 = {'trigger': 'done', 'source': 'recognizing', 'target': 'ready'}

    s_ready = {'name': 'ready', 'report': 'report()'}
    s_recognizing = {'name': 'recognizing', 'entry': 'recognize()', 'report': 'defer', 'recognize': 'defer'}

    stm = Machine(name='stm', transitions=[t_i0, t_01, t_10], states=[s_ready, s_recognizing], obj=recognizer)
    recognizer.stm = stm

    driver = Driver()
    driver.add_machine(stm)
    driver.start()

    print("[DRIVER]: driver started")

    # TODO: Temporary code to test the state machine
    driver.send('recognize', 'stm')
    driver.send('report', 'stm')
