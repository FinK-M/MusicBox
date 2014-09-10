import pygame.midi
import serial
import os
from sys import exit
from numpy import median, sqrt


def valMap(x, in_min, in_max, out_min, out_max):
    '''
    Maps a value "x" in a given range to value in a new range:
    x = a value
    in_min = minimum expected value of n
    in_max = maximum expected value of n
    out_min = minimum desired value of n
    out_max = maximum desired value of n
    '''
    return int(float((x - in_min) * (out_max - out_min) //
              (in_max - in_min) + out_min))


def medarray(n, array=[]):
    '''
    Median filter function:
    n = raw source to be filtered
    array = a blank array
    The length of the blank array determines the depth of the median filter
    '''
    for i in range(len(array)-1, 0, -1):
        array[i] = array[(i-1)]

    array[0] = n
    filt = median(array)

    return int(filt)

'''
Two blank arrays for the two values to be fed through the median filter
'''
raw0 = [0]*15
raw1 = [0]*15

pygame.init()
pygame.midi.init()


'''
Serial setup. Change "COM4" to /dev/ttyACM0 or similar for mac/linux
'''

BAUD_RATE = 115200
source = serial.Serial()

if os.name == "nt":
    source.port = "COM4"
else:
    source.port = "/dev/ttyACM0"

source.open()
source.baudrate = BAUD_RATE
print "Expected baud rate:", BAUD_RATE

print "%s name: %s input: %s output: %s opened: %s" %(pygame.midi.get_device_info(1))

GrandPiano = 0
AcousticGuitar = 24
Trumpet = 56
LeadSynth = 80
ChurchOrgan = 19

midiOut = pygame.midi.Output(1, 0)
midiOut.set_instrument(GrandPiano, 1)
midiOut.set_instrument(GrandPiano, 0)

c_maj = range(60, 73)
noteNames = ["C", "C#", "D", "D#", "E", "F", "F#",
             "G", "G#", "A", "A#", "B", "C"]
lastvel = [0]*26
lastsonic = 0

errors = 0
while True:
    try:
        #read string from serial port and split with commas as delimeters
        line = source.readline().split(",")[:36]
        #convert to array of ints ignoring special characters
        toks = [int(float(i)) for i in line]

        '''
        This section cuts note vels out of "toks" and sends them to midiOut.
        If vel of a key has not changed and is not zero the note is sustained.
        If the velocity is zero the note is turned off.
        '''

        vel = toks[2:28]
        for i in range(len(vel)):
            if i > 12:
                k = 1
            else:
                k = 0
            if lastvel[i] != vel[i] and vel[i] != 0 and vel[i] <= 400:
                lastvel[i] = vel[i]
                midiOut.note_on(c_maj[i % 13], valMap(vel[i], 0, 400, 124, 62),
                                channel=k)
                print noteNames[i % 13],
            elif vel[i] == 0 and lastvel[i] != vel[i]:
                lastvel[i] = vel[i]
                midiOut.note_off(c_maj[i % 13], lastvel[i],
                                 channel=k)
                if max(lastvel) == 0:
                    print ""
            else:
                lastvel[i] = vel[i]
                vel[i] = 0

        '''
        This section cuts the two distances from the rangefinders out of "toks"
        The lower value of the two is then consticted to 5000 and then mapped
        from 0 to 127. This becomes a value of pitch bend
        '''
        #left sensor distance passed through median filter
        sonicL = medarray(toks[0], raw0)
        #right sensor distance, also filtered
        sonicR = medarray(toks[1], raw1)

        if sonicL > 2000:
            sonicL = 2500
        elif sonicL < 250:
            sonicL = 250
        if sonicR > 2000:
            sonicR = 2500
        elif sonicR < 250:
            sonicR = 250

        #final value is taken to be lowest of L&R
        if sonicL < sonicR:
            sonic = sonicL
        else:
            sonic = sonicR

        sonic = int(valMap(sonic, 250, 2500, 0, 127))
        #midiOut.write_short(0xE0, sonic >> 7, sonic & 0x7F)

        '''
        This section takes the last value of toks as
        aftertouch from the resistive strip
        '''
        toks[28] = valMap(toks[28], 0, 200, 0, 500)
        toks[29] = valMap(toks[29], 150, 320, 0, 500)
        toks[30] = valMap(toks[30], 250, 450, 0, 500)
        toks[31] = valMap(toks[31], 300, 520, 0, 500)

        aTouch = int(sqrt(sum(a*a for a in toks[28:32])/len(toks[28:32])))

        print aTouch
        if aTouch < 250:
            aTouch = 0
        else:
            aTouch = int(valMap(aTouch, 150, 300, 0, 127))
        midiOut.write_short(0xD0, aTouch)

    except:
        errors += 1
        if errors > 20:
            exit("Too many read failures (>20)")

        continue
