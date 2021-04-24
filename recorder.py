from stmpy import Machine, Driver
import pyaudio
import wave
from appJar import gui

class Recorder:
    def __init__(self):
        self.recording = False
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 2
        self.fs = 44100  # Record at 44100 samples per second
        self.filename = "output.wav"
        self.p = pyaudio.PyAudio()

    # Creates the appJar gui, handling the button events
    def create_gui(self):
        self.app = gui()

        def extract_timer_name(label):
            label = label.lower()
            if 'stop' in label:
                return 'stop'
            elif 'record' in label:
                return 'record'
            elif 'play' in label:
                return 'play'
            return None

        self.app.startLabelFrame('Audio recording and playback')

        def on_button_pressed_start(title):
            command = extract_timer_name(title)
            self.stm.send(command)  # Start recording
            print("[ACTION]:", command)

        self.app.addButton('Record', on_button_pressed_start)
        self.app.addButton('Play', on_button_pressed_start)
        self.app.addButton('Stop recording', on_button_pressed_start)
        self.app.stopLabelFrame()

        self.app.go()

    def record(self):
        stream = self.p.open(format=self.sample_format,
                             channels=self.channels,
                             rate=self.fs,
                             frames_per_buffer=self.chunk,
                             input=True)
        self.frames = []  # Initialize array to store frames
        # Store data in chunks for 3 seconds
        self.recording = True
        while self.recording:
            data = stream.read(self.chunk)
            self.frames.append(data)
        print("[RECORDING]: done recording")
        # Stop and close the stream 
        stream.stop_stream()
        stream.close()
        # Terminate the PortAudio interface
        self.p.terminate()

    def stop(self):
        print("[ACTION]: stop")
        self.recording = False

    def process(self):
        print("[RECORDING]: processing")
        # Save the recorded data as a WAV file
        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()

    def play(self, filename):
        # filename = 'output.wav'
        # Set chunk size of 1024 samples per data frame
        chunk = 1024
        # Open the sound file 
        wf = wave.open(filename, 'rb')
        # Create an interface to PortAudio
        p = pyaudio.PyAudio()
        # Open a .Stream object to write the WAV file to
        # 'output = True' indicates that the sound will be played rather than recorded
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        # Read data in chunks
        data = wf.readframes(chunk)
        # Play the sound by writing the audio data to the stream
        while data != b'':
            stream.write(data)
            data = wf.readframes(chunk)

        # Close and terminate the stream and the PortAudio interface
        stream.close()
        p.terminate()

if __name__ == "__main__":
    recorder = Recorder()

    t0 = {'source': 'initial', 'target': 'ready'}
    t11 = {'trigger': 'play', 'source': 'ready', 'target': 'playing'}
    t12 = {'trigger': 'done', 'source': 'playing', 'target': 'ready'}

    t21 = {'trigger': 'record', 'source': 'ready', 'target': 'recording'}
    t22 = {'trigger': 'done', 'source': 'recording', 'target': 'processing'}
    t23 = {'trigger': 'done', 'source': 'processing', 'target': 'ready'}

    s_playing = {'name': 'playing', 'do': 'play("output.wav")'}
    s_recording = {'name': 'recording', 'do': 'record()', "stop": "stop()"}
    s_processing = {'name': 'processing', 'do': 'process()'}

    stm = Machine(name='stm', transitions=[t0, t11, t12, t21, t22, t23], states=[s_playing, s_recording, s_processing], obj=recorder)
    recorder.stm = stm

    driver = Driver()
    driver.add_machine(stm)
    driver.start()

    print("[DRIVER]: driver started")

    # Starts creating the GUI after the driver has started
    recorder.create_gui()
