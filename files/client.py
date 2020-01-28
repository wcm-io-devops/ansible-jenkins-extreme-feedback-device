import argparse
import os
import paho.mqtt.client as mqtt
import systemd.daemon
import yaml
import jinja2
import datetime
import os.path

# change to dir of the client script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

last_payload_file = "last_payload.yml"

def on_message(mqttc, obj, msg):
    payload = msg.payload.decode("utf-8")
    try:
        yml_payload = yaml.load(payload, Loader=yaml.SafeLoader)
        print("Got payload %s" % yml_payload)
        # store message to keep status on service restart
        f = open(last_payload_file, "w")
        yaml.dump(yml_payload, f)
        f.close()

        handle_payload(yml_payload)
    except:
        print("Unable to parse MQTT message as yaml.")

def handle_payload(payload):
    if not payload:
        print("No valid payload received")
        return

    BUILD_NUMBER = payload.get('BUILD_NUMBER', None)
    BUILD_RESULT = payload.get('BUILD_RESULT', None)
    BUILD_RESULT_COLOR = payload.get('BUILD_RESULT_COLOR', '#000000')
    BUILD_URL = payload.get('BUILD_URL', None)
    JENKINS_URL = payload.get('JENKINS_URL', None)
    JOB_BASE_NAME = payload.get('JOB_BASE_NAME', None)
    JOB_DISPLAY_URL = payload.get('JOB_DISPLAY_URL', None)
    JOB_NAME = payload.get('JOB_NAME', None)
    RUN_CHANGES_DISPLAY_URL = payload.get('RUN_CHANGES_DISPLAY_URL', None)
    MESSAGE_TIMESTAMP = int(payload.get('TIMESTAMP', 0))
    MESSAGE_TIME = datetime.datetime.fromtimestamp(MESSAGE_TIMESTAMP)
    RENDER_TIME = datetime.datetime.now()

    JOB_BASE_NAME = JOB_BASE_NAME.replace("%2F", "/")

    # render the values in the template and write to file!
    rendered_template = template.render(
        BUILD_NUMBER=BUILD_NUMBER,
        BUILD_RESULT=BUILD_RESULT,
        BUILD_RESULT_COLOR=BUILD_RESULT_COLOR,
        BUILD_URL=BUILD_URL,
        JENKINS_URL=JENKINS_URL,
        JOB_BASE_NAME=JOB_BASE_NAME,
        JOB_DISPLAY_URL=JOB_DISPLAY_URL,
        JOB_NAME=JOB_NAME,
        RUN_CHANGES_DISPLAY_URL=RUN_CHANGES_DISPLAY_URL,
        RENDER_TIME=RENDER_TIME,
        MESSAGE_TIME=MESSAGE_TIME,
        MESSAGE_TIMESTAMP=MESSAGE_TIMESTAMP,
    )

    f = open("/var/www/html/index.html", "w")
    f.write(rendered_template)
    f.close()

    if BUILD_RESULT == "SUCCESS" or BUILD_RESULT == "FIXED":
        setLight([0, 0, 1])
    elif BUILD_RESULT == "FAILURE" or BUILD_RESULT == "STILL FAILING":
        setLight([1, 0, 0])
    elif BUILD_RESULT == "UNSTABLE" or BUILD_RESULT == "STILL UNSTABLE":
        setLight([0, 1, 0])

def setLight(lights):
    print("setLight: %s" % (lights))
    cmd = "clewarecontrol -c 2"
    # build separate off and on commands to be able to place off before on statements in command line
    lights_off_args = []
    lights_on_args = []
    if device_sn is not None:
        cmd += " -d %s" % device_sn
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
device_sn = cfg['device_sn']

# we could also run .subscribe multiple times, but this is not recommended. Therefor we build tuples of (topic, qos)
tps = [(topic, 0) for topic in topics]

mqttc = mqtt.Client()

# load last message yaml_file when it exists
if (os.path.exists(last_payload_file)):
    print("Loading status from %s." % (last_payload_file))
    #try:
    file = open(last_payload_file, "r")
    last_payload = yaml.load(file, Loader=yaml.SafeLoader)
    print("last_payload %s." % (last_payload))
    handle_payload(last_payload)
    #except:
    #    print("Unable to load and parse %s as yaml" % (last_payload_file))

else:
    print("Initializing lights")
    setLight([0,0,0])

mqttc.on_message = on_message
mqttc.connect(host, 1883, 60)

mqttc.subscribe(tps)



# notify systemd that the service is ready
systemd.daemon.notify('READY=1')

mqttc.loop_forever()