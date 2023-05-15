from time import sleep
import serial
from gpiozero import CPUTemperature
import threading

def send(s, commands):
    s.flush()
    for i in range(0, len(commands)):
        print(f'Sending command: {commands[i][0]}')
        if commands[i][1][len(commands[i][1])-1] == '\x1A':
            s.write(commands[i][1].encode('ascii'))
            s.flush()
            continue
        else:
            s.write(f"{commands[i][1]}\r\n".encode('ascii'))
        s.flush()
        print('Response: ')
        while True:
            line = s.readline().decode('ascii')
            if line != '\r\n':
                print(line)
            if line == 'ERROR\r\n' and commands[i][0] != 'RESET':
                print('Received error, repeating...')
                i = i - 1
                continue
            if  line == 'OK\r\n' or line == '> \r\n' or line == '\r\n':
                break

def setup(port, baudrate):
    print('Setting up...')
    commands = [['RESET', '\x1A'], ['Echo On', 'ATE1'], ['Setup encoding to UTF-8', 'AT+CMGF=1']]
    s = serial.Serial(port, baudrate)
    if (not s.is_open):
        print(f'Cannot open port {port} at baudrate {baudrate}')
        exit()
    print(f'Conencted to port {s.name}')
    s.reset_input_buffer()
    s.reset_output_buffer()
    send(s, commands)
    print('Setup complete')
    return s


def tempMon(s, trigTemp, phoneNum, refreshRate, cooldown):
    commands = [['Setup send SMS', 'AT+CMGS="PHONENUM"'], ['Send SMS messsage', 'EMPTY']]
    global cooldownActive
    cooldownActive = False
    print(f'Started CPU temperature monitoring. Will check every {refreshRate} s if the temperature is exceeding {trigTemp} °C and will contact {phoneNum} if it is. The alert cooldown is {cooldown} s.')
    while True:
        cpuTemp = CPUTemperature().temperature
        print(f'The temperature is: {cpuTemp}')
        if cpuTemp > trigTemp and cooldownActive == False:
            commands[0][1] = f'AT+CMGS="{phoneNum}"'
            commands[1][1] = f"Your Raspberry Pi CPU is overheating! It's at {cpuTemp} degrees Celsius\x1A"
            send(s, commands)
            cooldownActive = True
            threading.Timer(cooldown, resetCooldown).start()

        sleep(refreshRate)

def resetCooldown():
    global cooldownActive
    cooldownActive = False
    print("Cooldown expired")

def main():
    port = '/dev/ttyACM0'
    baudrate = 115200
    trigTemp = 80.0
    phoneNum = '+PHONENUM'
    refreshRate = 1
    cooldown = 60
    s = setup(port, baudrate)
    tempMon(s, trigTemp, phoneNum, refreshRate, cooldown)

if __name__ == '__main__':
    main()
