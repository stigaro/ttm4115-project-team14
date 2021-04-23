import paho.mqtt.client as mqtt
import logging
import json
import base64
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
        self._logger = logging.getLogger(__name__)
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
        self._logger.debug("on_message(): topic: {}".format(msg.topic))
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.component.parse_message(payload)
        except Exception as err:
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
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
        print('logging under name {}.'.format(__name__))
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
        self.stm_driver.start(keep_active=True)
        self._logger.debug('Component initialization finished')

    
    def on_init(self):
        # Create and start MQTT client on init
        myclient = MQTT_Client(self)
        self.mqtt_client = myclient.client # for publishing/subscribing to broker ( wt.mqtt_client.publish )
        myclient.stm = self.stm
        myclient.start(MQTT_BROKER, MQTT_PORT)

        self.mqtt_client.subscribe(self.channel)
        print("{uuid}: listening on channel {channel}".format(uuid=self.uuid, channel=self.channel))
        
    def text_to_speech(self, text):
        this.tts.speak(str(text))

    def register(self):
        msg = {
            "command":"register",
            "uuid":self.uuid,
            "name":self.name
        }
        json_msg = json.dumps(msg)
        self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, json_msg)
        print(self.uuid)
 
    def start_recording(self):
        self.recorder.record()
    
    def stop_recording(self):
        self.recorder.stop()

    def parse_message(self, payload):
        if payload.get('command') == "message":
            self.stm.send("save_message", args=[payload])

    def save_message(self, payload):
        try:
            # Retreive message from payload
            wf = payload.get('data')
            data = base64.b64decode(wf)
            # self._logger.error(data)
            # Get queue length
            queue_number = 1
            with open(f'message_queue/{queue_number}.wav', 'wb') as fil:
                fil.write(data)
                self._logger.debug(f'Message saved to /message_queue/{queue_number}.wav')
        except:
            self._logger.error(f'Payload could not be read!')
        pass

    def check_message(self):
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
                    self.speak_empty_message()

    def reset_recording(self):
        pass
    
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
    
    def speak_recipient_not_found(self):
        msg = "Could not find recipient. Please try again."
        self.text_to_speech(msg)
    
    def speak_empty_message(self):
        msg = "Message was empty. Please try again."
        self.text_to_speech(msg)
    
    def speak_no_ack_received(self):
        msg = "Could not connect. Please try again"
        self.text_to_speech(msg)
    
    def speak_ok(self):
        msg = "Message sent"
        self.text_to_speech(msg)
    
    def blink(self):
        print("*Intense blinking*")
    
    def vibrate(self):
        print("Walkie goes brrrrrr...")

    def stop(self):
        # stop the MQTT client
        self.mqtt_client.loop_stop()
        # stop the state machine Driver
        self.stm_driver.stop()

    
######## TRANSITIONS
## syntax t[from][to] (state number)

t0 = {
    "source": "initial",
    "target": "listening",
    "effect": "on_init"
}
t11 = {
    "source": "listening",
    "target": "listening",
    "trigger": "register",
    "effect": "register"
}
t111 = {
    "source": "listening",
    "target": "receive_message",
    "trigger": "save_message",
}
t1111 = {
    'source': 'receive_message',
    'target': 'listening',
    'trigger': 'done',
}
t12 = {
    "source":"listening",
    "target":"record_message",
    "trigger":"talking",
    "effect":"start_recording"
}
t22 = {
    "source":"record_message",
    "target":"record_message",
    "trigger":"talking"
}
t23 = {
    "source":"record_message",
    "target":"processing",
    "trigger":"t",
}
t34 = {
    "source":"processing",
    "target":"send",
    "trigger":"done",
}
t351 = {
    "source":"processing",
    "target":"exception",
    "trigger":"recipient_not_found",
    "effect":"speak_recipient_not_found"
}
t352 = {
    "source":"processing",
    "target":"exception",
    "trigger":"empty_message",
    "effect":"speak_empty_message"
}
t45 = {
    "source":"send",
    "target":"exception",
    "trigger":"time_out",
    "effect":"speak_no_ack_received"
}
t51 = {
    "source":"exception",
    "target":"listening",
    "trigger":"error_done"
}
t41 = {
    "source":"send",
    "target":"listening",
    "trigger":"ack",
    "effect":"speak_ok"
}

transitions = [
    t0,
    t11,
    t111,
    t1111,
    t12,
    t22,
    t23,
    t34,
    t351,
    t352,
    t45,
    t51,
    t41
]

######## STATES
listening = {
    "name":"listening",
}
receive_message = {
    "name":"receive_message",
    "do": "save_message(*)",
    "save_message": "defer",
}
record_message = {
    "name":"record_message",
    "entry":"start_timer('t',3000)",
    "exit":"stop_recording"
}
processing = {
    "name":"processing",
    "entry":"check_message",
    "exit":"reset_recording"
}
send = {
    "name":"send",
    "entry":"start_timer('time_out',5000); send_data",
    "exit":"stop_timer('time_out')",
}
exception = {
    "name":"exception",
    "entry":"blink; vibrate"
}

states = [
    listening,
    receive_message,
    record_message,
    processing,
    send,
    exception
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
