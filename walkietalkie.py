from threading import Thread
from stmpy import Driver, Machine
from win32com.client import Dispatch

import paho.mqtt.client as mqtt

# TODO: choose proper MQTT broker address
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'ttm4115/team_14/walkietalkie'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_14/server'

class MQTT_Client:
    def __init__(self):
        self.count = 0
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print("on_connect(): {}".format(mqtt.connack_string(rc)))

    def on_message(self, client, userdata, msg):
        print("on_message(): topic: {}".format(msg.topic))
        
        json = json.dumps(msg)
        json["msg"] 
        self.stm_driver.send("message", msg.payload)

    def start(self, broker, port):

        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)

        self.client.subscribe(MQTT_TOPIC_INPUT)

        try:
            # line below should not have the () after the function!
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()
            
class WalkieTalkie:
    def on_init(self):
        print("Entering listening state...")
        
    def text_to_speak(self, text):
        speak = Dispatch("SAPI.SpVoice")
        speak.Speak('{}'.format(text))
        
    def start_recording(self):
        pass
    
    def stop_recording(self):
        pass
        
    def check_message(self):
        pass
    
    def reset_recording(self):
        pass
    
    def send_data(self):
        pass
    
    def speak_recipient_not_found(self):
        msg = "Could not find recipient. Please try again."
        self.text_to_speek(msg)
    
    def speak_empty_message(self):
        msg = "Message was empty. Please try again."
        self.text_to_speek(msg)
    
    def speak_no_ack_received(self):
        msg = "Could not connect. Please try again"
        self.text_to_speek(msg)
    
    def speak_ok(self):
        msg = "Message sent"
        self.text_to_speek(msg)
    
    def blink(self):
        print("*Intense blinking*")
    
    def vibrate(self):
        print("Walkie goes brrrrrr...")

    
######## TRANSITIONS
t0 = {"source": "initial",
      "target": "listening",
      "effect": "on_init"}

t1 = {
    "source":"listening",
    "target":"record_message",
    "trigger":"talking",
    "effect":"start_recording"
}
t2 = {
    "source":"record_message",
    "target":"record_message",
    "trigger":"talking"
}
t3 = {
    "source":"record_message",
    "target":"processing",
    "trigger":"t",
}
t3 = {
    "source":"processing",
    "target":"send",
    "trigger":"message_processed",
}
t4 = {
    "source":"processing",
    "target":"exception",
    "trigger":"recipient_not_found",
    "effect":"speak_recipient_not_found"
}
t5 = {
    "source":"processing",
    "target":"exception",
    "trigger":"empty_message",
    "effect":"speak_empty_message"
}
t6 = {
    "source":"send",
    "target":"exception",
    "trigger":"time_out",
    "effect":"speak_no_ack_received"
}
t6 = {
    "source":"exception",
    "target":"listening",
    "trigger":"error_done"
}
t7 = {
    "source":"send",
    "target":"listening",
    "trigger":"ack",
    "effect":"speak_ok"
}

transitions = [
    t0,
    t1,
    t2,
    t3,
    t4,
    t5,
    t6,
    t7
]

######## STATES
listening = {
    "name":"listening",
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
    record_message,
    processing,
    send,
    exception
]

walkie_talkie = WalkieTalkie()
walkie_talkie_machine = Machine(transitions=transitions, states=states, obj=walkie_talkie, name="walkie_talkie")
walkie_talkie.stm = walkie_talkie_machine

driver = Driver()
driver.add_machine(walkie_talkie_machine)

myclient = MQTT_Client()
walkie_talkie.mqtt_client = myclient.client # for publishing/subscribing to broker ( wt.mqtt_client.publish )
myclient.stm_driver = driver # for sending messages to stm ( stm_driver.send(msg, payload) )

driver.start()
myclient.start(MQTT_BROKER, MQTT_PORT)