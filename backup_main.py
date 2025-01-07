from machine import UART, I2C, Pin, Timer
import time
import network
import espnow
import ujson
import uasyncio as asyncio


# =========
# variables
# =========


nextion = UART(2, baudrate=9600, tx=14, rx=13)
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=100000)

max_voltage = 4.3
min_voltage = 3

step = 1
tension_etau = 0
pos_moteur = 0
interrupteur_data = 0


# =========
# fonctions
# =========


def connect():
    e = espnow.ESPNow()
    e.active(True)
    peer = b'\xb4\x8a\n\x8a/\x88'
    e.add_peer(peer)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    return e, peer

def voltToPercent(voltage):
    return int((voltage - min_voltage) / (max_voltage - min_voltage) * 100)

def send_with_retry(data, max_retries=10):
    for _ in range(max_retries):
        try:
            e.send(data)
            return True
        
        except OSError as err:
            if err.errno == 116:
                time.sleep(0.1)
                continue
            raise
    print("Message non envoye")
    return False

def send_nextion(data):
    nextion.write(data)
    nextion.write(b'\xff\xff\xff')

def update_nextion(pourcentage, tension_etau, etat_interrupteur, pos_moteur, pas_moteur):
        if etat_interrupteur == "O":
            pos_contact = 0
        else:
            pos_contact = 180

        if pourcentage > 100:
            pourcentage = 100

        if tension_etau > 100:
            tension_etau = 100

        send_nextion(f"j7.val=" + str(pourcentage))
        send_nextion(f"j6.val=" + str(tension_etau))
        send_nextion(f"j0.val=" + str(pos_moteur))
        send_nextion(f"z0.val=" + str(pos_contact))
        send_nextion(f"n5.val=" + str(pas_moteur))
        

# Fonction pour lire la valeur de la batterie
def lire_tension_batterie():
    data = i2c.readfrom(78, 2)  # Lit 2 octets depuis le périphérique I2C à l'adresse 78 (0x4E en hexadécimal)
    msb = data[0] << 6          # Décale l'octet de poids fort de 6 bits vers la gauche
    lsb = data[1] >> 2          # Décale l'octet de poids faible de 2 bits vers la droite
    return ((msb + lsb) * 5 / 1024)

async def getValues():
    global tension, pourcentage_batterie, decoded_msg, e, peer, tension_etau, interrupteur_data, pos_moteur

    while 1:
        _, msg = e.recv()
        if msg:
            try:
                data = ujson.loads(msg)
                interrupteur_data = data['interrupteur_msg']
                tension_etau = data['tension_msg']
                pos_moteur = data['pos_moteur']
                pas_moteur = data['pas_moteur']
                
            except ValueError:
                print("Erreur de décodage JSON")

        # Mettre à jour l'écran Nextion avec le pourcentage de batterie
        update_nextion(voltToPercent(lire_tension_batterie()), tension_etau, interrupteur_data, pos_moteur, pas_moteur)
        
        await asyncio.sleep(0.01)

# Fonction pour interpréter les données de Nextion
def interpret_data(data):
    global step

    if 'rs' in data:
        return "rs" # La tige est remise à zéro

    elif '10' in data:
        step = 10
        return "10"
    elif '25' in data:
        step = 25
        return "25"
    elif '1' in data:
        step = 1
        return "1"
    elif '5' in data:
        step = 5
        return "5"

    elif 'Long' in data:
        return "max"
    
    elif '+' in data:
        return "+" # La tige du moteur sort
    elif '-' in data:
        return "-" # La tige du moteur rentre

    return False

async def handle_Nextion():
    while 1:
        dataIn = nextion.read()  # Lecture des données série
        if dataIn:  # Vérifier si des données ont été reçues
            interpreted_data = interpret_data(dataIn)
            if interpreted_data:
                print('reçu', interpreted_data)
                send_with_retry(interpreted_data)
        await asyncio.sleep(0.1)
        
        
# =========
# main
# =========


# Connexion
print("Connexion ...", end="\r")
e, peer = connect()
print('Connexion Ok.')

async def main():
    await asyncio.gather(
        getValues(),
        handle_Nextion()
    )

asyncio.run(main())
