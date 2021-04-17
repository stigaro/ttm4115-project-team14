import speech_recognition as sr

recorder = Recorder()

t0 = {'source': 'initial', 'target': 'ready'}
t11 = {'trigger': 'play', 'source': 'ready', 'target': 'playing'}
t12 = {'trigger': 'done', 'source': 'playing', 'target': 'ready'}

t21 = {'trigger': 'record', 'source': 'ready', 'target': 'recording'}
t22 = {'trigger': 'done', 'source': 'recording', 'target': 'processing'}
t23 = {'trigger': 'done', 'source': 'processing', 'target': 'ready'}

s_playing = {'name': 'playing', 'do': 'play()'}
s_recording = {'name': 'recording', 'do': 'record()', "stop": "stop()"}
s_processing = {'name': 'processing', 'do': 'process()'}

stm = Machine(name='stm', transitions=[t0, t11, t12, t21, t22, t23], states=[s_playing, s_recording, s_processing], obj=recorder)
recorder.stm = stm

driver = Driver()
driver.add_machine(stm)
driver.start()
