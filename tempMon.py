from time import sleep
import serial
import threading
import platform
import io

def getOS():
    os = platform.system()
    if os == 'Windows':
        return 'Windows'
    elif os == 'Linux':
        try:
            with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
                if 'raspberry pi' in m.read().lower(): return 'Pi'
        except Exception: pass
        return 'Linux'
    else:
        return os

if getOS() == 'Pi':
    from gpiozero import CPUTemperature

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
        print('Response: ')
        while True:
            s.flush()
            line = s.readline()
            line = line.decode('ascii')
            if line != '\r\n' and line != ' \r\n':
                print(line, end="")
            if line == 'ERROR\r\n':
                if commands[i][2] == False:
                    print('Received error, repeating...')
                    i = i - 1
                    continue
                elif commands[i][2] == True:
                    break
            if  line == 'OK\r\n' or line == '> \r\n' or line == '\r\n':
                break

def setup(port, baudrate):
    print('Setting up...')
    commands = [['Echo On', 'ATE1', False], ['Setup message service to text mode', 'AT+CMGF=1', False]] # ['RESET', '\x1A', True], 
    try:
        s = serial.Serial(port, baudrate)
    except Exception as error:
        print(f'Cannot open port {port} at baudrate {baudrate} because an exception occuretd')
        print(error)
        exit()
    print(f'Conencted to port {s.name}')
    s.reset_input_buffer()
    s.reset_output_buffer()
    send(s, commands)
    print('Setup complete')
    return s


def tempMon(s, trigTemp, phoneNum, refreshRate, cooldown):
    if getOS() != 'Pi':
        print('Cannot run temperature monitoring on a non Raspberry Pi device!')
        exit()
    commands = [['Setup send SMS', 'AT+CMGS="PHONENUM"', False], ['Send SMS messsage', 'EMPTY', False]]
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


def measureSigQ(s, sigRepeat, sigDelay, pingIP, pingRepeat, pingDelay):
    commands = [['Signal quality', 'AT+CESQ', False]]
    for x in range(sigRepeat):
        send(s, commands)
        sleep(sigDelay)
    send(s, commands=[['Ping', f'AT+PING="{pingIP}",{pingRepeat},32,{pingDelay},5', True]])

def main():
    os = getOS()
    print(f'Running on {os}')
    if os == 'Windows':
        port = 'COM8'
    elif os == 'Linux' or os == 'Pi':
        port = '/dev/ttyACM0'
    else:
        print("Unsupported platform!")
        exit()
    baudrate = 115200
    trigTemp = 55.0
    phoneNum = '+PHONENUM'
    refreshRate = 1
    cooldown = 60
    s = setup(port, baudrate)

    #for i in range(1, 2):
    #    measureSigQ(s, 2, 1, '1.1.1.1', 5, i)

    tempMon(s, trigTemp, phoneNum, refreshRate, cooldown)

if __name__ == '__main__':
    main()
