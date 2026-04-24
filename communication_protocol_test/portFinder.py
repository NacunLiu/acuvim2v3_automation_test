import serial
from serial.tools import list_ports

def serial_ports():
    """List serial port names across Windows and Linux.

    Prefers pyserial's built-in discovery so containers and Linux hosts can
    expose devices such as `/dev/ttyUSB0` or `/dev/ttyACM0`.
    """
    result = []
    for port in list_ports.comports():
        try:
            s = serial.Serial(port.device)
            s.close()
            result.append(port.device)
        except (OSError, serial.SerialException):
            continue
    return result

if __name__ == '__main__':
    print(serial_ports())
        
                
