import pygame.midi
import serial
import numpy


def valMap(x, in_min, in_max, out_min, out_max):
    '''
    Equivalent of arduino map function:
    n = a value
    in_min = minimum expected value of n
    in_max = maximum expected value of n
    out_min = minimum desired value of n
    out_max = maximum desired value of n
    '''
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min


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
    filt = numpy.median(array)

    return int(filt)

'''
Two blank arrays for the two values to be fed through the median filter
'''
raw0 = [0]*7
raw1 = [0]*7

pygame.init()
pygame.midi.init()

print pygame.midi.get_device_info(1)

GRAND_PIANO = 0
LEAD_SYNTH = 80

midiOut = pygame.midi.Output(1, 0)
#midiOut.set_instrument(LEAD_SYNTH, 0)
midiOut.set_instrument(GRAND_PIANO, 0)

#Serial setup. Change "COM4" to /dev/ttyACM0 or similar for mac/linux
source = serial.Serial()
source.port = "COM4"
source.open()
source.baudrate = 115200

c_maj = range(60, 73)
lastvel = [0]*len(c_maj)
lastsonic = 0

while True:
    try:
        #read string from serial port and split with commas as delimeters
        line = source.readline().split(",")[:15]
        #convert to array of ints ignoring special characters
        toks = [int(float(i)) for i in line]

        '''
        This section cuts note vels out of "toks" and sends them to midiOut.
        If vel of a key has not changed and is not zero the note is sustained.
        If the velocity is zero the note is turned off.
        '''

        vel = toks[2:18]
        print vel,
        for i in range(len(vel)):
            if lastvel[i] != vel[i] and vel[i] != 0 and vel[i] <= 400:
                lastvel[i] = vel[i]
                midiOut.note_on(c_maj[i], valMap(vel[i], 0, 400, 124, 62), 0)
            elif vel[i] == 0:
                lastvel[i] = vel[i]
                midiOut.note_off(c_maj[i], lastvel[i], 0)
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

        #final value is taken to be lowest of L&R
        if sonicL < sonicR:
            sonic = sonicL
        else:
            sonic = sonicR
        #if final value > 5000, taken to be 5000
        if sonic > 5000:
            sonic = 5000
        sonic = int(valMap(sonic, 250, 5000, 0, 127))
        #midiOut.write_short(0xE0, sonic >> 7, sonic & 0x7F)

        print sonic,
        '''
        This section takes the last value of toks as
        aftertouch from the resistive strip
        '''
        if toks[14] < 400:
            aTouch = 0
        else:
            aTouch = valMap(toks[14], 400, 800, 0, 127)
        midiOut.write_short(0xD0, aTouch)
        print aTouch
    except:
        continue
