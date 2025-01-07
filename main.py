from machine import UART, I2C, Pin
import time
import network
import espnow
import ujson
import uasyncio as asyncio

nextion = UART(2, baudrate = 9600, tx = 14, rx = 13)
i2c = I2C(scl = Pin(22), sda = Pin(21), freq = 100000)

max_voltage = 4.3
min_voltage = 3

def connectEspNow() -> espnow:
    e = espnow.ESPNow()
    e.active(True)
    e.add_peer(b'\xb4\x8a\n\x8a/\x88')

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    return e

def voltToPercent(current_voltage: float) -> int:
    return int((current_voltage - min_voltage) / (max_voltage - min_voltage) * 100)

def sendData(data: str, max_retries: int = 10) -> None:
    for _ in range(max_retries):
        try:
            e.send(data)
            return
        
        except OSError as err:
            if err.errno == 116:
                time.sleep(0.1)
                continue
            raise
    print('Message non envoye')
    return

def sendNextion(data: str) -> None:
    nextion.write(data)
    nextion.write(b'\xff\xff\xff')

def updateDisplay(pupitre_voltage: int, etau_voltage: int, switch_state: str, motor_position: int, step_display: int, analog_button: int) -> None:
        switch_state_txt = 'Ouvert' if switch_state == 'C' else 'Ferme'
        gauge_orientation = int(180 * analog_button / 100)

        if pupitre_voltage > 100:
            pupitre_voltage = 100

        if etau_voltage > 100:
            etau_voltage = 100

        sendNextion(f'j7.val=' + str(pupitre_voltage))
        sendNextion(f'j6.val=' + str(etau_voltage))
        sendNextion(f'j0.val=' + str(motor_position))
        sendNextion(f'z0.val=' + str(gauge_orientation))
        sendNextion(f"n5.val=" + str(step_display))
        sendNextion(f't5.txt="{switch_state_txt}"')
        
def getBatteryVoltage() -> float:
    data = i2c.readfrom(78, 2)
    msb = data[0] << 6 
    lsb = data[1] >> 2
    return (msb + lsb) * 5 / 1024

async def receiveValues(e: espnow) -> None:
    while 1:
        _, msg = e.recv()
        if msg:
            try:
                data = ujson.loads(msg)
                switch_state = data['switch_state']
                etau_voltage = data['etau_voltage']
                motor_position = data['motor_position']
                step_display = data['step_display']
                analog_button = data['analog_button']
                
            except ValueError:
                print('Erreur de décodage JSON')

        updateDisplay(voltToPercent(getBatteryVoltage()), etau_voltage, switch_state, motor_position, step_display, analog_button)
        
        await asyncio.sleep(0.01)

def getDecodedData(data: str) -> str:
    if 'rs' in data:
        return 'rs' # La tige est remise à zéro

    elif '10' in data:
        return '10'
    elif '25' in data:
        return '25'
    elif '1' in data:
        return '1'
    elif '5' in data:
        return '5'

    elif 'Long' in data:
        return 'max'
    
    elif '+' in data:
        return '+' # La tige du moteur sort
    elif '-' in data:
        return '-' # La tige du moteur rentre

    return 

async def handleNextion() -> None:
    while 1:
        received_data = nextion.read()
        if received_data:
            decoded_data = getDecodedData(received_data)
            if decoded_data:
                print(f'{decoded_data=}')
                sendData(decoded_data)
        await asyncio.sleep(0.1)
        
if __name__ == '__main__':
    print('Connexion ...', end='\r')
    e = connectEspNow()
    print('Connexion Ok.')

    async def main():
        await asyncio.gather(
            receiveValues(e),
            handleNextion()
        )

    asyncio.run(main())


