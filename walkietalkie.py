import os
import paho.mqtt.client as mqtt
import logging
import json
import base64
from appJar import gui
from recognizer import Recognizer
from recorder import Recorder
from stmpy import Driver, Machine
from threading import Thread
from tts import Speaker
from uuid import uuid4

MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_BASE = 'ttm4115/team_14/'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_14/command'

class MQTT_Client:
    def __init__(self, component):
        self.count = 0
        self.component = component
        # callback methods
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print("on_connect(): {}".format(mqtt.connack_string(rc)))
        self.stm.send("register")

    def on_message(self, client, userdata, msg):
        self.component._logger.debug("on_message(): topic: {}".format(msg.topic))
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.component.parse_message(payload)
        except Exception as err:
            self.component._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return

    def start(self, broker, port):
        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)
        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()

class WalkieTalkie:
    def __init__(self, transitions, states):
        self.payload = {}
        self._logger = logging.getLogger(__name__)
        self._logger.info('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        self.recorder = Recorder()
        self.tts = Speaker()

        self.uuid = uuid4().hex
        self.uuid = "122ec9e8edda48f8a6dd290747acfa8c"
        self.channel = "{server}{uuid}".format(server=MQTT_TOPIC_BASE,uuid=self.uuid)

        self.name = "Christopher"
        walkie_talkie_machine = Machine(transitions=transitions, states=states, obj=self, name="{}_walkie_talkie".format(self.name))
        self.stm = walkie_talkie_machine

        self.stm_driver = Driver()
        self.stm_driver.add_machine(walkie_talkie_machine)
        self.stm_driver.start()
        self._logger.debug('Component initialization finished')

    def create_gui(self):
        self.app = gui()

        def extract_btn_name(label):
            label = label.lower()
            if 'send <' in label:
                return 'talking'
            elif 'replay <' in label:
                return 'request_replay_message'
            elif 'replay' in label:
                return 'replay_message'
            elif 'next' in label:
                return 'next'
            elif 'play' in label:
                return 'play_message'
            return None

        self.app.startLabelFrame('Walkie talkie')

        def on_button_pressed_start(title):
            command = extract_btn_name(title)
            self.stm.send(command)
            print("[ACTION]:", command)
            print("[ACTION]:", self.stm.state)

        self.app.addButton('Send <name>', on_button_pressed_start)
        self.app.addButton('Play', on_button_pressed_start)
        self.app.addButton('Replay', on_button_pressed_start)
        self.app.addButton('Next', on_button_pressed_start)
        self.app.addButton('Replay <name>', on_button_pressed_start)
        self.app.stopLabelFrame()
        self.app.go()

    def on_init(self):
        # Create and start MQTT client on init
        client = MQTT_Client(self)
        self.mqtt_client = client.client # for publishing/subscribing to broker
        client.stm = self.stm
        client.start(MQTT_BROKER, MQTT_PORT)

        self.mqtt_client.subscribe(self.channel)
        print("{uuid}: listening on channel {channel}".format(uuid=self.uuid, channel=self.channel))

        # Create GUI in a new thread
        th = Thread(target=self.create_gui)
        th.start()
        
    def text_to_speech(self, text):
        self.tts.speak(str(text))

    def register(self):
        msg = {
            "command":"register",
            "uuid":self.uuid,
            "name":self.name
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json_msg)
        print(self.uuid)
    
    # Add state machine to this v
    def start_recording(self):
        self.recorder.record()
    
    def stop_recording(self):
        self.recorder.stop()
    
    def reset_recording(self):
        # TODO
        pass
    
    # Parses server responses
    def parse_message(self, payload):
        if payload.get('command') == "message":
            self.stm.send("save_message", args=[payload])
        elif payload.get('data'):
            self.stm.send('replay_save_message', args=[payload])

    def save_message(self, payload):
        try:
            # Retreive message from payload
            wf = payload.get('data')
            data = base64.b64decode(wf)
            # Get queue length and saves message in the FIFO order
            queue_number = len(os.listdir("message_queue"))+1
            with open(f'message_queue/{queue_number}.wav', 'wb') as fil:
                fil.write(data)
                self._logger.debug(f'Message saved to /message_queue/{queue_number}.wav')
        except:
            self._logger.error(f'Payload could not be read!')

    def play_replay_message(self, payload):
        try:
            # Retreive message from payload
            wf = payload.get('data')
            data = base64.b64decode(wf)
            with open(f'replay_message.wav', 'wb') as fil:
                fil.write(data)
                self._logger.debug(f'Message saved to replay_message.wav')
            self.recorder.play("replay_message.wav")
            self.stm.send("replay_finished")
        except:
            # TODO
            self._logger.error(f'Payload could not be read!')
            self.stm.send("replay_finished")
            pass
    
    def play_message(self):
        # Check queue length
        queue_length = len(os.listdir("message_queue"))
        if queue_length > 0:
            self._logger.info(f'Playing message 1/{queue_length}!')
            self.recorder.play("message_queue/1.wav")
            self.stm.send('message_played')
        else:
            # self.tts_error('ok')
            # TODO
            self.stm.send('message_played')
            pass
    
    def load_next_message_in_queue(self):
        queue_folder = "message_queue"
        queue_length = len(os.listdir(queue_folder))
        if queue_length > 1:
            self.iterate_queue()
        else:
            # self.tts_error('no_ack_received')
            # TODO
            pass
    
    # Iterates queue in FIFO order deleting the first file and shifting the filenames to the left
    def iterate_queue(self):
        queue_folder = "message_queue"
        for i, filename in enumerate(os.listdir(queue_folder)):
            if i == 0:
                os.remove(f"{queue_folder}/{filename}")
            else:
                os.rename(f"{queue_folder}/{filename}", f"{queue_folder}/{i}.wav")

    # Request replay message from the server
    def play_latest_user_message(self):
        name = "bob ross"
        uuid = self.uuid
        msg = {
            "device_id_from": uuid,
            "device_owner_name_to": name,
            "command":"replay",
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json_msg)

    def check_message(self):
        # Should be fixed
        msg = self.Recognizer.recognize()
        if len(msg) < 2:
            self.speak_empty_message()
        else:
            #check if the message does not contain any normal words, if so, we call it empty
            usual_words = ["hello", "help", "thanks"] #liste med ofte brukte ord, lang
            for word in usual_words:
                if word in msg:
                    break
                else:
                    self.error("empty_message")

    def send_data(self):
        filename = self.recorder.filename
        byte_data = open(filename, 'rb')
        data = b64encode(byte_data)
        msg = {
            "device_id_from":self.uuid,
            "device_owner_name_to":"recipient",
            "command":"message",
            "data":data
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT,json_msg)
    
    def tts_error(self, exception):
        if exception == "recipient_not_found":
            msg = "Could not find recipient. Please try again."
        elif exception == "empty_message":
            msg = "Message was empty. Please try again."
        elif exception == "no_ack_received":
            msg = "Could not connect. Please try again"
        elif exception == "ok":
            msg = "Message sent"
        self.text_to_speech(msg)
        self._logger.debug(msg)
    
    def blink(self):
        print("*Intense blinking*")
    
    def vibrate(self):
        print("Walkie goes brrrrrr...")

    def stop(self):
        # stop the MQTT client
        self.mqtt_client.loop_stop()
        # stop the state machine Driver
        self.stm_driver.stop()

    
# TRANSITIONS
transitions = [
    # Initial
    {
        "source": "initial",
        "target": "listening",
        "effect": "on_init"
    },
    # Register
    {
        "source": "listening",
        "target": "listening",
        "trigger": "register",
        "effect": "register"
    },
    # Receive message
    {
        "source": "listening",
        "target": "receive_message",
        "trigger": "save_message",
    },
    {
        'source': 'receive_message',
        'target': 'listening',
        'trigger': 'done',
    },
    # Play message
    {
        "source": "listening",
        "target": "playing",
        "trigger": "play_message",
    },
    {
        "source": "playing",
        "target": "playing",
        "trigger": "replay_message",
    },
    {
        "source": "playing",
        "target": "playing",
        "trigger": "next",
        "effect": "load_next_message_in_queue",
    },
    {
        'source': 'playing',
        'target': 'listening',
        'trigger': 'time_out',
        'effect': 'iterate_queue',
    },
    # Request replay message
    {
        "source": "listening",
        "target": "replay",
        "trigger": "request_replay_message",
    },
    {
        'source': 'replay',
        'target': 'playing_replay',
        'trigger': 'replay_save_message',
    },
    {
        'source': 'playing_replay',
        'target': 'listening',
        'trigger': 'replay_finished',
    },
    # Record message
    {
        "source":"listening",
        "target":"record_message",
        "trigger":"talking",
        "effect":"start_recording"
    },
    {
        "source":"record_message",
        "target":"record_message",
        "trigger":"talking"
    },
    {
        "source":"record_message",
        "target":"processing",
        "trigger":"t",
    },
    {
        "source":"processing",
        "target":"send",
        "trigger":"done",
    },
    # Processing and Send exceptions
    {
        "source":"processing",
        "target":"exception",
        "trigger":"recipient_not_found",
        "effect":"tts_error('recipient_not_found')"
    },
    {
        "source":"processing",
        "target":"exception",
        "trigger":"empty_message",
        "effect":"tts_error('empty_message')"
    },
    {
        "source":"send",
        "target":"exception",
        "trigger":"time_out",
        "effect":"tts_error('no_ack_received')"
    },
    {
        "source":"exception",
        "target":"listening",
        "trigger":"error_done"
    },
    {
        "source":"send",
        "target":"listening",
        "trigger":"ack",
        "effect":"tts_error('ok')"
    },
]


# STATES
states = [
    {
        "name":"listening",
    },
    {
        "name":"receive_message",
        "do": "save_message(*)",
        "save_message": "defer",
    },
    {
        "name":"replay",
        "do": "play_latest_user_message()",
    },
    {
        "name":"playing_replay",
        "do": "play_replay_message(*)",
        "replay_save_message": "defer",
    },
    {
        "name":"playing",
        "do": "play_message()",
        "entry": "stop_timer('time_out')",
        "message_played": "start_timer('time_out',3000)",
    },
    {
        "name":"record_message",
        "entry":"start_timer('t',3000)",
        "exit":"stop_recording"
    },
    {
        "name":"processing",
        "entry":"check_message",
        "exit":"reset_recording"
    },
    {
        "name":"send",
        "entry":"start_timer('time_out',5000); send_data",
        "exit":"stop_timer('time_out')",
    },
    {
        "name":"exception",
        "entry":"blink; vibrate"
    },
]

# Logging
debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

walkie_talkie = WalkieTalkie(transitions, states)
