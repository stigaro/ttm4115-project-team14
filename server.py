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
    # TODO: fix this
    def __init__(self, name, duration, component):
        self._logger = logging.getLogger(__name__)
        self.name = name
        self.duration = duration
        self.component = component

    def started(self):
        self.stm.start_timer('t', self.duration * 1000)
        self._logger.debug('New timer {} with duration {} started.'
                           .format(self.name, self.duration))

    def timer_completed(self):
        self._logger.debug('Timer {} expired.'.format(self.name))
        self.stm.terminate()

    def report_status(self):
        self._logger.debug('Checking timer status.'.format(self.name))
        time = int(self.stm.get_timer('t') / 1000)
        message = 'Timer {} has about {} seconds left'.format(self.name, time)
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)

    def create_machine(timer_name, duration, component):
        timer_logic = ServerStm(name=timer_name, duration=duration, component=component)
        t0 = {'source': 'initial',
              'target': 'active',
              'effect': 'started'}
        t1 = {
            'source': 'active',
            'target': 'completed',
            'trigger': 't',
            'effect': 'timer_completed'}
        t2 = {
            'source': 'active',
            'trigger': 'report',
            'target': 'active',
            'effect': 'report_status'}
        timer_stm = stmpy.Machine(name=timer_name, transitions=[t0, t1, t2],
                                  obj=timer_logic)
        timer_logic.stm = timer_stm
        return timer_stm

class Server:
    def on_connect(self, client, userdata, flags, rc):
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))
        # self._logger.debug('Payload is {}'.format(msg.payload))
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return
        command = payload.get('command')
        self._logger.debug('Command in message is {}'.format(command))
        if command == "message": # {"device_id_from": 1, "device_id_to": 2, "command" : "message", "data": "b64encoded data"}
            # Get sender
            sender = payload.get('device_id_from')
            # Get receiver
            receiver = payload.get('device_id_to')
            # Save message to database
            data = payload.get('data')
            wf = base64.b64decode(data)
            with open(f'stored_messages/{sender}-{receiver}.wav', 'wb') as fil:
                fil.write(wf)
                self._logger.debug(f'Message saved to /stored_messages/{sender}-{receiver}.wav')
            # Send to receiver
            payload = {"device_id_from": sender, "device_id_to": receiver, "data": data}
            self.mqtt_client.publish(MQTT_TOPIC_OUTPUT+str(receiver), json.dumps(payload))
            self._logger.debug(f'Message sent to {receiver}!')
        elif command == "replay": # {"device_id_from": 1, "device_id_to": 2, "command" : "replay"}
            # Get sender
            sender = payload.get('device_id_from')
            # Get receiver
            receiver = payload.get('device_id_to')
            # Retreive message from database
            wf = open(f'stored_messages/{receiver}-{sender}.wav', 'rb')
            data = base64.b64encode(wf.read())
            # print(data)
            # Send message to receiver
            payload = {"device_id_from": sender, "device_id_to": receiver, "data": data.decode()}
            self.mqtt_client.publish(MQTT_TOPIC_OUTPUT+str(sender), json.dumps(payload))
            self._logger.debug(f'Message replayed to {sender}!')
        else:
            self._logger.error('Unknown command {}. Message ignored.'.format(command))
        # timer_name = payload.get('name')
        # print(type(self))
        # self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)

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