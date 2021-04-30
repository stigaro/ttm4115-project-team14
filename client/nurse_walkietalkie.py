import os
import paho.mqtt.client as mqtt
import logging
import json
import base64
import time
import sys
from appJar import gui
from recognizer import get_state_machine
from recorder import Recorder
from stmpy import Driver, Machine
from threading import Thread, Lock
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
        # Callback methods
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print("on_connect(): {}".format(mqtt.connack_string(rc)))
        self.component.stm.send("register")

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
    def __init__(self, transitions, states, debug):
        self.payload = {}
        self._logger = logging.getLogger(__name__)
        self._logger.info('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')
        self.debug = debug
        self.app = None
        self.lock = Lock()
        self.recorder = Recorder(self)
        self.text_to_speech = Speaker()

        self.uuid = uuid4().hex
        if self.debug:
            self.uuid = "122ec9e8edda48f8a6dd290747acfa8c"
        self.channel = "{server}{uuid}".format(server=MQTT_TOPIC_BASE,uuid=self.uuid)

        self.name = "christopher"
        stm_walkie_talkie_name = "{}_walkie_talkie".format(self.name)
        walkie_talkie_machine = Machine(transitions=transitions, states=states, obj=self, name=stm_walkie_talkie_name)
        self.stm = walkie_talkie_machine

        recognizer_stm = get_state_machine('stm_recognizer', [stm_walkie_talkie_name])

        self.stm_driver = Driver()
        self.stm_driver.add_machine(walkie_talkie_machine)
        self.stm_driver.add_machine(recognizer_stm)
        self.stm_driver.start()
        self._logger.debug('Component initialization finished')

    def create_gui(self):
        self.app = gui("Walkie Talkie", "320x568", bg='yellow')
        self.app.setStretch("both")
        self.app.setSticky("")
        self.app.setBgImage("images/bg.gif")

        if self.debug == True:
            self.app.setInPadding([30,40])
            self.app.setPadding([0,50])
        self.app.addLabel("status", "State: STATUS", 0, 0)
        self.app.setLabelBg("status", "#3e3e3e")
        self.app.setLabelFg("status", "white")

        def on_button_pressed_start(label):
            label = label.lower()
            command = label
            if 'stop' in label:
                self.stop_recording()
                command = "stop"
            elif 'send <' in label:
                self.stm.send("send", kwargs={'action': 'send', 'argument': 'bob ross'})
                command = "send"
            elif 'replay <' in label:
                self.stm.send("replay", kwargs={'action': 'replay', 'argument': 'bob ross'})
                command = "replay"
            elif 'replay' in label:
                self.stm.send("replay")
                command = "replay"
            elif 'next' in label:
                self.stm.send("next") 
                command = "next"
            elif 'play' in label:
                self.stm.send("play")
                command = "play"
            print("[ACTION]:", command)
            print("[STATE]:", self.stm.state)
        
        if self.debug == True:
            self.app.setPadding([0,0])
            self.app.setInPadding([60,40])
            self.app.startLabelFrame("Debug panel",1,0)
            self.app.setStretch("both")
            self.app.setSticky("news")
            self.app.addButton('Send <name>', on_button_pressed_start)
            self.app.addButton('Stop recording', on_button_pressed_start)
            self.app.addButton('Play', on_button_pressed_start)
            self.app.addButton('Replay', on_button_pressed_start)
            self.app.addButton('Next', on_button_pressed_start)
            self.app.addButton('Replay <name>', on_button_pressed_start)
            self.app.stopLabelFrame()
        else:
            self.app.addLabel("padding", "", 1, 0)
        self.update_led(False)
        self.update_status('LISTENING')
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
    
    # Text-to-speech
    def tts(self, text):
        th = Thread(target=self.text_to_speech.speak, args=[str(text)])
        th.start()
        self._logger.debug(text)

    def register(self):
        msg = {
            "command":"register",
            "uuid":self.uuid,
            "name":self.name
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json_msg)
        print(self.uuid)

    def query_server(self, **kwargs): # check if recipient/sender is registered
        if kwargs.get("argument") and kwargs.get("action"):
            msg = {
                "command":"query",
                "device_id_from":self.uuid,
                "recipient_name": kwargs.get("argument")
            }
            json_msg = json.dumps(msg)
            self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json_msg)
        else:
            self.stm.send("time_out")

        '''
        request:
        {"device_id_from": uuid, "recipient_name": name, "command" : "query" }
 
        response:
        {"device_id_from": sender, "recipient_name": name, "exists": true/false}
        '''

    def start_recording(self):
        self.update_status("RECORDING")
        self.recorder.record()

    def stop_recording(self):
        self.update_status("STOP RECORDING")
        self.recorder.stop()
    
    # Parses server responses
    def parse_message(self, payload):
        if payload.get('command') == "message":
            self.stm.send("save_message", args=[payload])
        elif payload.get('exists') == True: # if recipient exists
            self.recipient = payload.get("recipient_name")
            self.stm.send("query_ok")
        elif payload.get('exists') == False: # if recipient does not exists
            self.stm.send("query_not_found")
        elif payload.get('data'):
            self.stm.send('replay_save_message', args=[payload])
    
    def threaded_save(self, lock, payload):
        lock.acquire()
        try:
            sender_name = payload.get('device_owner_name_from')
            self.tts(f"Received message from {sender_name}")
            # Retreive message from payload
            wf = payload.get('data')
            data = base64.b64decode(wf)
            # Get queue length and saves message in the FIFO order
            queue_number = len(os.listdir("message_queue"))
            with open(f'message_queue/{queue_number}.wav', 'wb') as fil:
                fil.write(data)
                self._logger.debug(f'Message saved to /message_queue/{queue_number}.wav')
        except:
            self._logger.error(f'Payload could not be read!')
        lock.release()
        self.iterate_queue(False)

    def save_message(self, payload):
        th = Thread(target=self.threaded_save, args=[self.lock,payload])
        th.start()
        th.join()

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
        except: # Should never happen, but added as insurance so the program doesn't throw an error and stops
            self._logger.error(f'Payload could not be read!')
    
    def play_message(self):
        self.update_status("PLAYING")
        # Check queue length
        queue_folder = "message_queue"
        queue_length = len(os.listdir(queue_folder))
        if self.check_message_queue(1):
            self._logger.info(f'Playing message 1/{queue_length}!')
            self.recorder.play(f"{queue_folder}/1.wav")
            self.stm.send('message_played')
            self.update_led(False, 1)
        else:
            self.stm.send("queue_empty")
    
    def load_next_message_in_queue(self):
        # Iterates queue in FIFO order deleting the first file and shifting the filenames to the left
        if self.check_message_queue(2): # if there are more than 1, it is safe to iterate
            self.iterate_queue()
        else:
            self.iterate_queue()
            self.stm.send("queue_empty")

    def check_message_queue(self, i): # returns true if there are more than i messages left in queue
        if len(os.listdir("message_queue")) > i:
            return True
        return False
    
    def threaded_iterate(self, lock, remove):
        lock.acquire()
        queue_folder = "message_queue"
        num = 1
        listdir = os.listdir(queue_folder)
        listdir.sort()
        for filename in listdir:
            if filename.split(".")[0] == "1" and num == 1 and remove:
                os.remove(f"{queue_folder}/{filename}")
            else:
                if filename != ".gitkeep":
                    os.rename(f"{queue_folder}/{filename}", f"{queue_folder}/{num}.wav")
                    num += 1
        self.update_led(False)
        lock.release()

    def iterate_queue(self, remove = True):
        th = Thread(target=self.threaded_iterate, args=[self.lock, remove]);
        th.start()
        th.join()

    # Request replay message from the server
    def get_latest_user_message(self):
        self.update_status("REPLAYING")
        name = self.recipient
        uuid = self.uuid
        msg = {
            "device_id_from": uuid,
            "device_owner_name_to": name,
            "command":"replay",
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json_msg)

    def send_data(self):
        filename = self.recorder.filename
        byte_data = open(filename, 'rb')
        data = base64.b64encode(byte_data.read())
        msg = {
            "device_id_from":self.uuid,
            "device_owner_name_to": self.recipient,
            "command": "message",
            "data": data.decode()
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT,json_msg)
     
    def update_status(self, text):
        if self.app != None:
            label = "State:"+text
            self.app.setLabel("status", label)

    def update_led(self,is_error, queue_pad = 0):
        if self.app != None:
            if is_error:
                self.app.setBgImage("images/bg_red.gif")
            else:
                if self.check_message_queue(1+queue_pad): # check if there are more than 1 messages in queue
                    self.app.setBgImage("images/bg_green.gif")
                else:
                    self.app.setBgImage("images/bg.gif")

    def vibrate(self):
        self.recorder.play("vibrate.wav")
        self._logger.debug("Walkie goes brrrrrr...")

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
    # Play message
    {
        "source": "listening",
        "target": "playing",
        "trigger": "play",
    },
    {
        "source": "playing",
        "target": "playing",
        "trigger": "replay",
        "effect": "stop_timer('time_out')",
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
    {
        'source': 'playing',
        'target': 'exception',
        'trigger': 'queue_empty',
        "effect": "tts('Message queue is empty')"
    },
    # Request replay message
    {
        "source": "listening",
        "target": "check_replay_sender",
        "trigger": "replay",
        "effect": "query_server(*)",
    },
    {
        "source": "check_replay_sender",
        "target": "exception",
        "trigger": "query_not_found",
        "effect": "tts('Recipient not found')"
    },
    {
        "source": "check_replay_sender",
        "target": "exception",
        "trigger": "time_out",
        "effect": "tts('Connection lost')"
    },
    {
        "source": "check_replay_sender",
        "target": "replay",
        "trigger": "query_ok"
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
    # Check recipient
    {
        "source":"listening",
        "target":"check_recipient",
        "trigger":"send",
        "effect": "query_server(*)",
    },
    {
        "source":"check_recipient",
        "target":"exception",
        "trigger":"query_not_found",
        "effect":"tts('Recipient not found')"
    },
    {
        "source":"check_recipient",
        "target":"exception",
        "trigger":"time_out",
        "effect":"tts('Connection lost')"
    },
    {
        "source":"check_recipient",
        "target":"recording",
        "trigger":"query_ok"
    },
    # Recording
    {
        "source":"recording",
        "target":"listening",
        "trigger":"done",
        "effect":"send_data; tts('Message sent')"
    },
    # Exceptions
    {
        "source":"exception",
        "target":"listening",
        "trigger":"error_done"
    },
]


# STATES
states = [
    {
        "name":"listening",
        "do": "update_status('LISTENING')",
        "entry": "update_led(False)",
        "register": "register()",
        "save_message": "save_message(*)",
    },
    {
        "name":"check_recipient",
        "entry":"start_timer('time_out',3000)",
        "exit":"stop_timer('time_out')",
        "save_message":"save_message(*)",
    },
    {
        "name":"check_replay_sender",
        "entry":"start_timer('time_out',3000)",
        "exit":"stop_timer('time_out')",
        "save_message":"save_message(*)",
    },
    {
        "name":"replay",
        "do": "get_latest_user_message()",
        "save_message": "save_message(*)",
    },
    {
        "name":"playing_replay",
        "do": "play_replay_message(*)",
        "replay_save_message": "defer",
        "save_message": "save_message(*)",
    },
    {
        "name":"playing",
        "do": "play_message()",
        "entry": "stop_timer('time_out')",
        "message_played": "start_timer('time_out',3000)",
        "save_message": "save_message(*)",
    },
    {
        "name": "recording",
        "do": "start_recording()",
        "save_message": "save_message(*)",
    },
    {
        "name": "exception",
        "do": "vibrate",
        "entry": "update_led(True); update_status('EXCEPTION'); start_timer('error_done',3000)",
        "save_message": "save_message(*)",
    },
]

debug = False
debug_level = logging.ERROR
if len(sys.argv) > 1:
    if sys.argv[1] in ["-d", "--debug"]:
        debug_level = logging.DEBUG
        debug = True

# Logging
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

if __name__ == "__main__":
    walkie_talkie = WalkieTalkie(transitions, states, debug)
