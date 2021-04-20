import paho.mqtt.client as mqtt
import stmpy
import logging
from threading import Thread
import json
import wave
import base64

MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'ttm4115/team_14/command'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_14/'


class ServerStm:
    def __init__(self, name, payload, component):
        self._logger = logging.getLogger(__name__)
        self.name = name
        self.component = component
        self.payload = payload;
        self.response_message = "";
        self.mqtt_topic_output = MQTT_TOPIC_OUTPUT;
        self.handling_success = True

    def started(self):
        self._logger.debug("")
        self._logger.debug("[Server]: started...")
        if self.payload:
            self.stm.send('incoming_request')

    def handle_request(self):
        self._logger.debug("[Server]: handling request...")
        command = self.payload.get('command')
        # Check for command validity
        if command == "message":
            self.handling_success = self.payload.get('device_id_from') and self.payload.get('device_id_to') and self.payload.get('data');
        elif command == "replay":
            self.handling_success = self.payload.get('device_id_from') and self.payload.get('device_id_to');
        else:
            self.handling_success = False
        # Trigger finished_handling
        self.stm.send('finished_handling')

    def handle_compound_transition(self):
        self._logger.debug("[Server]: finished handling...")
        if self.handling_success:
            self._logger.debug("[Server]: accepted - transitioning to Build")
            return 'build'
        else:
            self._logger.debug("[Server]: denied - transitioning to Send")
            return 'send';
    
    def build_response(self):
        self._logger.debug("[Server]: building response...")
        command = self.payload.get('command')
        try:
            if command == "message": # {"device_id_from": 1, "device_id_to": 2, "command" : "message", "data": "b64encoded data"}
                # Get sender
                sender = self.payload.get('device_id_from')
                # Get receiver
                receiver = self.payload.get('device_id_to')
                # Save message to database
                data = self.payload.get('data')
                self._logger.debug(f'{sender}, {receiver}, {data}')
                wf = base64.b64decode(data)
                with open(f'stored_messages/{sender}-{receiver}.wav', 'wb') as fil:
                    fil.write(wf)
                    self._logger.debug(f'Message saved to /stored_messages/{sender}-{receiver}.wav')
                # Send to receiver
                payload = {"device_id_from": sender, "device_id_to": receiver, "data": data}
                self.response_message = json.dumps(payload)
                self.mqtt_topic_output = MQTT_TOPIC_OUTPUT+str(receiver)
            elif command == "replay": # {"device_id_from": 1, "device_id_to": 2, "command" : "replay"}
                # Get sender
                sender = self.payload.get('device_id_from')
                # Get receiver
                receiver = self.payload.get('device_id_to')
                # Retreive message from database
                wf = open(f'stored_messages/{receiver}-{sender}.wav', 'rb')
                self._logger.debug(f'Retrieved message from /stored_messages/{receiver}-{sender}.wav to be replayed')
                data = base64.b64encode(wf.read())
                # Send message to receiver
                payload = {"device_id_from": sender, "device_id_to": receiver, "data": data.decode()}
                self.response_message = json.dumps(payload)
                self.mqtt_topic_output = MQTT_TOPIC_OUTPUT+str(sender)
        except:
            self.handling_success = False;
            return self.stm.send('response_failed')
        self.stm.send('response_built')

    def send_message(self):
        if self.handling_success:
            self._logger.debug("[Server]: response message sent")
            self.component.mqtt_client.publish(self.mqtt_topic_output, self.response_message) 
        else:
            self._logger.error("[Server]: error message sent")
        # Terminates the stm
        self.stm.terminate()
        
    def create_machine(server_name, payload, component):
        server_logic = ServerStm(server_name, payload, component)
        # regular transitions
        t0 = {
            'source': 'initial',
            'target': 'passive',
            'effect': 'started'}
        t1 = {
            'source': 'passive',
            'target': 'handle',
            'trigger': 'incoming_request',
            'effect': 'handle_request'}
        # compound transition
        t2 = {
            'source':'handle',
            'trigger':'finished_handling',
            'targets': 'send build',
            'function': server_logic.handle_compound_transition}
        # regular transitions
        t3 = {
            'source': 'send',
            'trigger': 'message_sent',
            'target': 'passive'}
        t4 = {
            'source': 'build',
            'trigger': 'response_built',
            'target': 'send'}
        t5 = {
            'source': 'build',
            'trigger': 'response_failed',
            'target': 'send'}
        # states
        s0 = {
            'name': 'build',
            'entry': 'build_response'}
        s1 = {
            'name': 'send',
            'entry': 'send_message'}
        server_stm = stmpy.Machine(name=server_name, transitions=[t0,t1,t2,t3,t4,t5], states=[s0,s1],
                                  obj=server_logic)
        server_logic.stm = server_stm
        return server_stm

class Server:
    def on_connect(self, client, userdata, flags, rc):
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return
        command = payload.get('command')
        self._logger.debug('Command in message is "{}"'.format(command))

        # Create stm logic for every message request
        server_stm = ServerStm.create_machine("server"+str(len(self.stm_driver._stms_by_id)), payload, self)
        # Adds the machine to the driver to start it
        self.stm_driver.add_machine(server_stm)
        return;

    def __init__(self):
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(MQTT_TOPIC_INPUT)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        # we start the stmpy driver, without any state machines for now
        self.stm_driver = stmpy.Driver()
        self.stm_driver.start(keep_active=True)
        self._logger.debug('Component initialization finished')

    def stop(self):
        # stop the MQTT client
        self.mqtt_client.loop_stop()
        # stop the state machine Driver
        self.stm_driver.stop()


# logging.DEBUG: Most fine-grained logging, printing everything
# logging.INFO:  Only the most important informational log items
# logging.WARN:  Show only warnings and errors.
# logging.ERROR: Show only error messages.
debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

t = Server()