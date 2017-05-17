import time
import paho.mqtt.client as mqtt

class BaseClient():
    
    # initialize client
    def __init__(self,
                 broker,
                 stdout,
                 style,
                 verbosity = 1):
        
        # initialize client
        self.stdout = stdout
        self.style = style
        self.broker = broker
        self.verbosity = verbosity

        if self.broker['CLIENT_ID']:
            self.client = mqtt.Client(self.broker['CLIENT_ID'],
                                      self.broker['CLEAN_SESSION'])
        else:
            self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        
        # default message handler
        self.client.on_message = self.on_message

        if self.broker['USERNAME'] and self.broker['PASSWORD']:
            self.client.username_pw_set(self.broker['USERNAME'],
                                        self.broker['PASSWORD'])
            
        self.client.connect(self.broker['HOST'],
                            self.broker['PORT'],
                            self.broker['KEEPALIVE'])

        # populated?
        self.populated = False

    def on_connect(self, client, userdata, flags, rc):
        
        if rc:
            self.stdout.write(
                self.style.ERROR("*> Could not connect to brocker. Return code '" + str(rc) + "'"))
            return False

        # success!
        if self.verbosity > 0:
            self.stdout.write(self.style.SUCCESS(">> Connected to the MQTT brocker '{}:{}'".format(self.broker['HOST'], self.broker['PORT'])))

        return True

    def on_message(self, client, userdata, msg):
        pass
    
    # disconnect
    def disconnect(self):
        self.client.disconnect()
        
    # loop forever
    def loop_forever(self):
        self.client.loop_forever()
