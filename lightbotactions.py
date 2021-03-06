import RPi.GPIO as GPIO
import subprocess
import time
import urllib.request
import signal
import mpd

valid_target = {'0': 15, '1': 16, '2': 11, '3': 12}
valid_state = {'on': GPIO.HIGH, 'off': GPIO.LOW}
mpd_server = {'host': 'localhost', "port": 6600}

prev_vol = None

def turn_off(greeting = False):
	global prev_vol
	client = mpd.MPDClient()
	client.connect(**mpd_server)
	try:
		prev_vol = int(client.status()["volume"])
	except e:
		prev_vol = 60
	print("Got "+str(prev_vol))
	if greeting:
		try:
			subprocess.check_call(["aplay", "/home/simark/audio_samples/graine.wav"])
		except:
			pass
	client.setvol(0)
	client.disconnect()

def turn_on(greeting = False):
	global prev_vol
	if prev_vol:
		client = mpd.MPDClient()
		client.connect(**mpd_server)
		print("Set "+str(prev_vol))
		client.setvol(prev_vol)
		prev_vol = None
		client.disconnect()
		if greeting:
			try:
				subprocess.check_call(["aplay", "/home/simark/audio_samples/francois.wav"])
			except:
				pass

def get_plafond_status():

	res = urllib.request.urlopen("http://station6.dorsal.polymtl.ca:9898").read()
	if res == b'1':
		return True
	elif res == b'0':
		return False
	else:
		raise Exception()


def handler(signum, frame):
	print("SIGNAL COT")
	presence = get_plafond_status()

	if presence:
		turn_on(True)
	else:
		turn_off(True)


class LightbotActions:
	def __init__(self, irc):
		GPIO.setmode(GPIO.BOARD)
		for x in valid_target:
			GPIO.setup(valid_target[x], GPIO.OUT)
		self.irc = irc
		self.last_toggle = 0

		signal.signal(signal.SIGUSR1, handler)
		#This next line doesn't seem to do anything
		signal.siginterrupt(signal.SIGUSR1, False)

	def action_light_turn(self, from_, chan, msg, parts):
		if len(parts) != 2:
			return
		
		target = parts[0]
		state = parts[1]

		if target not in valid_target or state not in valid_state:
			return

		value = valid_state[state]
		pin = valid_target[target]
		GPIO.output(pin, value)
		self.irc.privmsg(chan, "Light " + target + " is now " + state)

	def action_light_status(self, from_, chan, msg, parts):
		if len(parts) == 0:
			for t in sorted(valid_target.keys()):
				value = "on" if GPIO.input(valid_target[t]) else "off"
				self.irc.privmsg(chan, "Light " + str(t) + ": " + value)
			self.irc.privmsg(chan, "Light local: " + ("on" if get_plafond_status() else "off"))
			
		elif len(parts) == 1:
			t = parts[0]
			if t in valid_target:
				value = "on" if GPIO.input(valid_target[t]) else "off"
				self.irc.privmsg(chan, "Light " + str(t) + ": " + value)
	
	def action_toggle(self, from_, chan, msg, parts):
		t = time.time()
		if t - self.last_toggle >= 5:
			self.last_toggle = t
			try:
				signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})
				subprocess.call(["/home/simark/avr/serieViaUSB/serieViaUSB", "-e", "-f", "/home/simark/avr/serieViaUSB/fichier"])
				self.irc.privmsg(chan, "Your wish is my command")
				#time.sleep(1)
				if get_plafond_status():
					self.irc.privmsg(chan, "Light is now on")
				else:
					self.irc.privmsg(chan, "Light is now off")
			except:
				raise
			finally:
				signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGUSR1})
		else:
			self.irc.privmsg(chan, "You have to wait 5 seconds between two toggles.")

	def action_light(self, from_, chan, msg, parts):
		if len(parts) == 0:
			return
		
		cmd = parts.pop(0)

		if cmd == 'turn':
			self.action_light_turn(from_, chan, msg, parts)
		elif cmd == 'toggle':
			self.action_toggle(from_, chan, msg, parts)
		elif cmd == 'status':
			self.action_light_status(from_, chan, msg, parts)

	def on_chanmsg(self, from_, chan, msg):
		parts = msg.split()[1:]
		self.action_light(from_, chan, msg, parts)
