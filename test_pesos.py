import math

# 1. Función Sigmoide 
def sigmoide(x):
    return 1 / (1 + math.exp(-x))

# 2. Definimos los pesos y bias exactos 
W_oculta = [
    [-2.189, -0.858, 1.560, -9.708], # Nodo 1
    [-8.092, 12.491, -3.768, -0.484], # Nodo 2
    [-0.688, 0.107, 0.367, -4.260],   # Nodo 3
    [1.011, 1.130, 0.144, -0.540]     # Nodo 4
]
b_oculta = [3.892, -0.537, 3.022, -0.633]

W_salida = [-2.879, -2.158, 1.163, 0.010]
b_salida = 0.733

# 3. Simulamos un cliente 
ingreso = 5000 / 10000.0  # Normalizado
deuda = 200 / 10000.0     # Normalizado
edad = 30 / 100.0         # Normalizado
similitud = 0.95          # De 0 a 1
X = [ingreso, deuda, edad, similitud]

# 4. EJECUCIÓN DE LOS PESOS 
h = []
for i in range(4):
    suma = sum(X[j] * W_oculta[i][j] for j in range(4)) + b_oculta[i]
    resultado_nodo = sigmoide(suma)
    h.append(resultado_nodo)
    print(f"Activación Nodo Oculto {i+1}: {resultado_nodo:.4f}")

neta = sum(h[i] * W_salida[i] for i in range(4)) + b_salida


print("--- VERIFICACIÓN DE PESOS DEL MODELO ---")
print(f"Pesos Capa Oculta (W1): {W_oculta}")
print(f"Bias Capa Oculta (b1): {b_oculta}")
print(f"Pesos Capa Salida (W2): {W_salida}")
print(f"Bias Capa Salida (b2): {b_salida}")
print("----------------------------------------\n")
