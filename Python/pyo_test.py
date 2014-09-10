from pyo import *
import serial
import numpy
import pyo

source = serial.Serial()
source.port = "COM4"
source.open()
source.baudrate = 115200

s = Server(sr=44100, nchnls=2, buffersize=1024, duplex=0)

out_devices = pyo.pa_get_output_devices()
od_index = 0
print out_devices
for od in out_devices[0]:
    if "ASIO" in od:
        pai = int(out_devices[1][od_index])
        s.setOutputDevice(pai)
        print "Found ASIO device, using device " + str(pai)
        break
    od_index += 1

s.boot()


class keySound(PyoObject):
    def __init__(self, pitch=440, amp=0):
        self._pitch = pitch
        self._amp = amp
        self._pitchSig = Sig(pitch)
        self._ampSig = Sig(amp)
        self._pitchOut = Port(self._pitchSig, risetime=.1, falltime=.1)
        self._ampOut = Port(self._ampSig, risetime=.1, falltime=.1)
        self._sound = Osc(SquareTable(), freq=self._pitchOut,
                          mul=self._ampOut).out()
        self._base_objs = []

    def __dir__(self):
        return ["pitch", "amp"]

    def setPitch(self, x):
        self._pitch = x
        self._pitchSig.value = x

    def setAmp(self, x):
        self._amo = x
        self._ampSig.value = x

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, x):
        self.setPitch(x)

    @property
    def amp(self):
        return self._amp

    @amp.setter
    def amp(self, x):
        self.setAmp(x)


def medarray(n, array=[]):

    for i in range(len(array)-1, 0, -1):
        array[i] = array[(i-1)]

    array[0] = n
    filt = numpy.median(array)

    return int(filt)


def valMap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

s.start()

raw0 = [0]*3
raw1 = [0]*3
raw2 = [0]*3

scale = [262, 277, 293, 311, 330, 350, 370, 392, 415, 440, 466, 493, 523]
wave = SawTable()

dist_pval = Sig(value=220)
dist_aval = Sig(value=0.5)
dist_dval = Sig(value=0)
dist_rval = Sig(value=0)


distosc = Osc(wave, freq=Port(dist_pval, risetime=.1, falltime=0.1),
              mul=Port(dist_aval, risetime=.1, falltime=.5)).out()
distosc = Harmonizer(distosc, transpo=-7.0, feedback=.5)
distosc = Disto(distosc, drive=dist_dval)
distosc = Freeverb(distosc, damp=dist_rval).out()

Keys = [keySound(pitch=scale[i]).out() for i in range(len(scale))]

while True:
    try:
        #read string from serial port and split with commas as delimeters
        line = source.readline().split(",")[:16]
        #convert to array of 4 ints ignoring special characters

        toks = [int(float(i)) for i in line]
        #dist = toks[:3]
        vel = toks[2:15]
        #xy = toks[13:15]
        #touch = toks[15:]
        print vel

        if min(dist) <= 10000:
            dist_aval.setValue(0.5)

            if dist[0] == min(dist):
                dist_pval.setValue(valMap(int(medarray(dist[0], raw0)),
                                          0, 10000, 100, 2000))

            elif dist[1] == min(dist):
                dist_pval.setValue(valMap(int(medarray(dist[1], raw1)),
                                          0, 10000, 100, 2000))

            elif dist[2] == min(dist):
                dist_pval.setValue(valMap(int(medarray(dist[2], raw2)),
                                          0, 10000, 100, 2000))
        else:
            dist_aval.setValue(0)


        for key in range(len(Keys)):
            if vel[key] != 0 and vel[key] <= 500:
                Keys[key].setAmp(float(500-vel[key])/1000)
            else:
                Keys[key].setAmp(0)

        dist_dval.setValue(float(valMap(xy[0], 225, 800, 0, 10))/10)
        dist_rval.setValue(float(valMap(xy[1], 380, 745, 0, 10))/10)


    except:
        print "error"
