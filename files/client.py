import argparse
import os
import paho.mqtt.client as mqtt
import systemd.daemon
import yaml
import jinja2

# change to dir of the client script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def on_message(mqttc, obj, msg):
    payload = msg.payload.decode("utf-8")
    yml_payload = yaml.load(payload, Loader=yaml.SafeLoader)
    print("Got message %s" % yml_payload)

    BUILD_RESULT = yml_payload['BUILD_RESULT']
    PROJECT_URL = yml_payload['BUILD_RESULT']
    CULPRITS = yml_payload['BUILD_RESULT']
    BUILD_NUMBER = yml_payload['BUILD_RESULT']
    JOB_DISPLAY_URL = yml_payload['JOB_DISPLAY_URL']
    RUN_CHANGES_DISPLAY_URL = yml_payload['RUN_CHANGES_DISPLAY_URL']

    # render the values in the template and write to file!
    rendered_template = template.render(payload=yml_payload)
    f = open("/var/www/html/index.html", "w")
    f.write(rendered_template)
    f.close()

    if BUILD_RESULT == "SUCCESS":
        setLight([0, 0, 1])
    elif BUILD_RESULT == "FAILURE":
        setLight([1, 0, 0])
    elif BUILD_RESULT == "UNSTABLE":
        setLight([0, 1, 0])


def setLight(lights):
    cmd = "clewarecontrol -c 2"
    # build separate off and on commands to be able to place off before on statements in command line
    lights_off_args = []
    lights_on_args = []
    if device is not None:
        cmd += " -d %s" % device
    # build command line
    for idx, status in enumerate(lights):
        curr_light_cmd = "-as %d %d" % (idx, status)
        if status == 0:
            lights_off_args.append(curr_light_cmd)
        else:
            lights_on_args.append(curr_light_cmd)


    cmd = "%s %s %s" % (cmd, " ".join(lights_off_args), " ".join(lights_on_args))

    print("Execute cmd: %s" % (cmd))

    os.system(cmd)


parser = argparse.ArgumentParser(description="Foobar write some doc...")
parser.add_argument("--config", dest="config", default="config.yml", type=str, help="Path to the configuration file.")
args = parser.parse_args()

# define the template to render
templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "index.html.j2"
template = templateEnv.get_template(TEMPLATE_FILE)

config_path = args.config

# load config yaml file
with open(config_path, 'r') as cfg_ymlfile:
    cfg = yaml.load(cfg_ymlfile, Loader=yaml.SafeLoader)

mqttCfg = cfg['mqtt']
topics = mqttCfg['topics']
host = mqttCfg['host']
device = cfg['device']

print("Initializing lights")
setLight([0,0,0])

# we could also run .subscribe multiple times, but this is not recommended. Therefor we build tuples of (topic, qos)
tps = [(topic, 0) for topic in topics]

mqttc = mqtt.Client()
mqttc.on_message = on_message
mqttc.connect(host, 1883, 60)

mqttc.subscribe(tps)

# notify systemd that the service is ready
systemd.daemon.notify('READY=1')

mqttc.loop_forever()