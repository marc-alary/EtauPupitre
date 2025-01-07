import network

# Activer le mode STA (Station)
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)

# Obtenir l'adresse MAC
mac_address = sta_if.config('mac')

print("Adresse MAC de l'ESP32:", mac_address)