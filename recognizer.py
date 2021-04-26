import speech_recognition as sr
from stmpy import Machine, Driver


# noinspection PyTypeChecker
# noinspection PyBroadException
class Recognizer:
    """
    Class that represents a state machine which detects audio and recognizes it.
    If audio was found, recognized AND was activated with the keyword 'recognition_keyword'
    the state machine will send the recognition as argument to the observers in a transition.
    """

    def __init__(self, recognition_keyword='communicator', stm_observers=[]):
        self.stm: Machine = None
        self.stm_observers: list = stm_observers
        self.microphone = sr.Microphone()
        self.speech_converter = sr.Recognizer()
        self.audio = None
        self.recognition_word = recognition_keyword
        self.recognition = ""

    def update_observers(self):
        # Prepares recognition. By default we only send the last activation keyword string
        recognition_string = self.recognition.split(self.recognition_word)[-1].lstrip()
        print("[OBSERVER_UPDATE]: '{}'".format(recognition_string))
        for stm_observer in self.stm_observers:
            try:
                self.stm.driver.send('adressed', stm_observer, args=[{
                    'recognition_word': self.recognition_word,
                    'recognition_string': recognition_string
                }])
            except Exception:
                print("WARNING; Recognizer raised exception when sending to observer")
                continue  # We ignore any exceptions.

    def was_adressed(self):
        if self.recognition_word in self.recognition:
            print("[COMPOUND-TRUE]: Recognition keyword used")
            self.update_observers()
        else:
            print("[COMPOUND-FALSE]: Recognition keyword not used")

        return 'listening'

    def listen(self):
        print("\n\n[LISTENING]: Listening for audio")
        with self.microphone as microphone:
            self.speech_converter.adjust_for_ambient_noise(microphone)
            self.audio = self.speech_converter.listen(microphone)
        self.stm.send("new_audio")

    def recognize(self):
        try:
            print('[RECOGNIZING]: Recognizing found audio')
            self.recognition = self.speech_converter.recognize_google(self.audio).lower()
            self.stm.send("recognized")

        except Exception:
            print('[RECOGNIZING]: Was unable to recognize audio')
            self.recognition = ""
            self.stm.send("recognition_error")


def get_state_machine(name: str, observers: list):
    recognizer = Recognizer( recognition_keyword='lisa', stm_observers=observers)

    t_i0 = {'source': 'initial', 'target': 'listening'}
    t_01 = {'trigger': 'new_audio', 'source': 'listening', 'target': 'recognizing'}
    t_10_a = {'trigger': 'recognition_error', 'source': 'recognizing', 'target': 'listening'}
    t_10_b = {'trigger': 'recognized', 'source': 'recognizing', 'function': recognizer.was_adressed}

    s_listening = {'name': 'listening', 'entry': 'listen'}
    s_recognizing = {'name': 'recognizing', 'entry': 'recognize'}

    stm = Machine(name=name, transitions=[t_i0, t_01, t_10_a, t_10_b], states=[s_listening, s_recognizing], obj=recognizer)
    recognizer.stm = stm

    return stm


if __name__ == "__main__":
    recognizer = Recognizer()

    t_i0 = {'source': 'initial', 'target': 'listening'}
    t_01 = {'trigger': 'new_audio', 'source': 'listening', 'target': 'recognizing'}
    t_10_a = {'trigger': 'recognition_error', 'source': 'recognizing', 'target': 'listening'}
    t_10_b = {'trigger': 'recognized', 'source': 'recognizing', 'function': recognizer.was_adressed}

    s_listening = {'name': 'listening', 'entry': 'listen'}
    s_recognizing = {'name': 'recognizing', 'entry': 'recognize'}

    stm = Machine(name='stm_recognizer', transitions=[t_i0, t_01, t_10_a, t_10_b], states=[s_listening, s_recognizing], obj=recognizer)
    recognizer.stm = stm

    print("[DRIVER]: driver starting")
    driver = Driver()
    driver.add_machine(stm)
    driver.start()

