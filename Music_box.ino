/*********************************************************

This program allows an arduino to read a keyboard matrix
circuit and print key velocities to the serial port.

The matrix is presumed to contain an even number of rows
("numRows" or "r"), and an arbritray number of columns
("numCols" or "c"). It is assumed that even rows correspond
to the primary switches and odd rows to secondary switches.

Assumptions:
-Each key has diode protection to prevent "ghost presses"
-The number of keys (numKeys) is <= r * c

Written by Finlay Knops-Mckim (C) 2014

**********************************************************/
#define numKeys 13
#define numCols 7
#define numRows 4

//Set to true to detect velocity on white keys
#define useVel false

//Set up pins for rows and columns
const int Columns[2][numCols] = {{22, 23, 24, 25, 26, 27, 28}, {34, 35, 36, 37, 38, 39, 40}};
const int Rows[2][numRows] = {{30, 31, 32, 33}, {42, 43, 44, 45}};
const int analogPins[] = {A0,A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11};

//Create current and past state variables for all switches
int State[2][numCols][numRows], lastState[2][numCols][numRows];

//Create arrays for switch times and lag between switches
long SW[2][numKeys], lag[2][numKeys];

//Set up pins for rangefinders
const int trigs[] = {50, 52};
const int echos[] = {51, 53};

volatile bool echoed[] = {false, false};
volatile unsigned long lastmicros[2], currentmicros[2], distance[2];

void setup() 
{
  //Ensure this matches the baudrate in the python script
  Serial.begin(115200);

  //Set all analogue pins to input
  for(int i = 0; i < 12; i++)
  {
    pinMode(analogPins[i], INPUT);
  }

  //Setup pins from ultrasonic rangefinders
  for(int i = 0; i < 2; i++)
  {
    pinMode(trigs[i],OUTPUT);
    pinMode(echos[i],INPUT);
  }

  //Ultrasonic interrupts
  attachInterrupt(echos[0], out0, FALLING);  //Interrupt at end of echo measurement signal
  attachInterrupt(echos[1], out1, FALLING);  //Interrupt at end of echo measurement signal 

  for(int k = 0; k < 2; k++)
  {
    //Set columns as inputs with pullup resistors on
    for(int c = 0; c < numCols; c++){
      pinMode(Columns[k][c], INPUT);
      digitalWrite(Columns[k][c], HIGH);
    }
    
    //Set rows as outputs with starting value of +Vcc
    for(int r = 0; r < numRows; r++){
      pinMode(Rows[k][r], OUTPUT);
      digitalWrite(Rows[k][r], HIGH);
    }
  }
}

void loop()
{
  //Uncomment below line to print run time for each loop
  //runTime();

  //Trigger the ultrasonic rangefinders IF an echo has already been recieved.
  for(int i = 0; i < 2; i++)
  {
    if(echoed[i] == true && micros() - currentmicros[i] > 60000);
    {
      trigRange(i);
      currentmicros[i] = micros();
    }
  }
  Serial.print(distance[0]);
  Serial.print(",");
  Serial.print(distance[1]);
  Serial.print(",");

  //Iterate through all rows and columns
  for(int k = 0; k < 2; k++)
  {
    for(int c = 0; c < numCols; c++)
    {
      for(int r = 0; r < numRows; r++)
      if(useVel == true)
        velKey(c, r, k);
      else
        dumbKey(c, r, k);
    }
  }
  
  //Iterate through all keys and print lag to serial
  for(int k = 0; k < 2; k++)
  {
    for(int i = 0; i < numKeys; i++)
    {
      Serial.print(lag[k][i]);
      Serial.print(",");
    }
  }

  //iterate through 8 FSR strips and print value to serial.
  for(int i = 4; i < 12; i++)
  {
    Serial.print(analogRead(analogPins[i]));
    Serial.print(",");
  }
  Serial.println("");
}

/*
Function to tigger a rangefinder. Pulls "trig" pin low,
waits for 2 us, then pulls it high for 10 us.
The "echoed" variable is then set to false to signify that
a pulse has been sent but not yet recieved.

i == rangefinder number, +ve int.
*/
void trigRange(int i)
{
  digitalWrite(trigs[i],LOW);
  delayMicroseconds(2);

  digitalWrite(trigs[i],HIGH);
  lastmicros[i] = micros();
  delayMicroseconds(10);
  
  digitalWrite(trigs[i],LOW);
  echoed[i] = false;
}

/*
Determines states of all keys and velocities of white notes
Calls readSwitch to determine state of each switch, and findN
to get the key number. If a black key is on a velocity of 50 is
sent.

c == column reference, +ve int
r == row reference, +ve int
k == keyboard reference, +ve int
*/
void velKey(int c, int r, int k)
{
  readSwitch(c, r, k);
  int n = findN(c, r);

  if(n == 1 || n == 3 || n == 6 || n == 8 || n == 10)
  {
    if(r % 2 == 0)
      lag[k][n] =  50 * long(State[k][c][r]);
  }
  else
    findLag(c, r, k, n);
}

/*
Treats all keys as on/off, where on is a velocity of 50.

c == column reference, +ve int
r == row reference, +ve int
k == keyboard reference, +ve int
*/
void dumbKey(int c, int r, int k)
{
  readSwitch(c, r, k);
  int n = findN(c, r);

  if(r % 2 == 0)
      lag[k][n] =  50 * long(State[k][c][r]);
}

/*
Returns a key number from given c and r.

c == column reference, +ve int
r == row reference, +ve int
*/
int findN(int c, int r)
{
  //Sets equivalent key number
  int n = c;

  //Rows 0 & 1 are keys 0 - 6, Rows 2 & 3 are keys 7 - 12
  if(r >= 2 && r < 4)
    n += 7;

  return n;
}

/*
Updates the state variable for a given switch.
Sets the matrix to measure a given switch.

c == column reference, +ve int
r == row reference, +ve int
k == keyboard reference, +ve int
*/
void readSwitch(int c, int r, int k)
{
  //Update the previous switch state
  lastState[k][c][r] = State[k][c][r];

  //Set row "r" to GND
  digitalWrite(Rows[k][r], LOW);

  //Update the current switch state (0 = Off, 1 = On)
  State[k][c][r] = !digitalRead(Columns[k][c]);

  //Reset row "r" to +Vcc
  digitalWrite(Rows[k][r], HIGH);
}

/*
Finds the time between the first and second switches of a key
being pressed and sets the lag variable for that key.

c == column reference, +ve int
r == row reference, +ve int
k == keyboard reference, +ve int
n == key number
*/
void findLag(int c, int r, int k, int n)
{
  //If the state has changed
  if(State[k][c][r] != lastState[k][c][r])
  {
    if(State[k][c][r] == 1)
    {
      //If the switch is primary, set on time to current time
      //and reset the lag
      if(r % 2 == 0)
      {
        SW[k][n] = millis();
        lag[k][n] = 0;
      }
      //If the switch is secondary and the corresponding primary
      //is on, set lag to current time - on time
      else if(State[k][c][r - 1] == 1)
        lag[k][n] = millis() - SW[k][n];

      if(lag[k][n] > 1000)
        lag[k][n] = 0;
    }
    //Else the state is off
    else
      lag[k][n] = 0;
  }
}

/*
This function can be placed in the main loop to print out
how long each loop takes to execute. 
*/
void runTime()
{
  static long check = 0;
  Serial.println(micros() - check);
  check = micros();
}

/*
ISR for the first rangefinder attached to echos[0].
Finds the length of the pulse recieved and saves it.
457 is the rough time taken from the rangefinder firing
to it sending the pulse so is removed.
*/
void out0()
{
  distance[0] = micros() - lastmicros[0] - 457;
  echoed[0] = true; 
}

/*
ISR for the second rangefinder attached to echos[1].
*/
void out1()
{
  distance[1] = micros() - lastmicros[1] - 457;
  echoed[1] = true;
}