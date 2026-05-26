"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import Webcam from "react-webcam"; // IMPORTANTE: Asegúrate de tener instalada esta librería

interface Registro {
  _id: string;
  nombres: string;
  apellidos: string;
  dni: string;
  fecha_nacimiento: string;
  genero: string;
  edad?: string; 
}

export default function Home() {
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [loading, setLoading] = useState(true);
  const [escaneando, setEscaneando] = useState(false);
  
  // Estados de edición
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [tempFecha, setTempFecha] = useState("");

  // Estado para mostrar la cámara web con la máscara
  const [mostrarWebcam, setMostrarWebcam] = useState(false);

  const galleryInputRef = useRef<HTMLInputElement>(null);
  const webcamRef = useRef<Webcam>(null);

  const API_URL = "https://proyecto-kyc-ucv.onrender.com";

  const cargarDatos = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/registros`);
      const data = await res.json();
      if (data.status === "success") {
        setRegistros(data.data);
      }
    } catch (error) {
      console.error("Error al cargar la base de datos:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarDatos();
  }, []);

  const eliminarRegistro = async (id: string) => {
    const confirmar = window.confirm("¿Estás seguro de que quieres eliminar este registro?");
    if (!confirmar) return;

    try {
      const res = await fetch(`${API_URL}/eliminar/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (data.status === "success") {
        setRegistros(registros.filter((reg) => reg._id !== id));
      } else {
        alert("No se pudo eliminar: " + data.message);
      }
    } catch (error) {
      alert("Error de conexión al intentar eliminar.");
    }
  };

  const guardarCambio = async (id: string) => {
    try {
      const res = await fetch(`${API_URL}/actualizar/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fecha_nacimiento: tempFecha }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setEditandoId(null);
        cargarDatos(); 
      } else {
        alert("Error al actualizar: Asegúrate de usar el formato DD/MM/AAAA");
      }
    } catch (error) {
      alert("Error de conexión al intentar actualizar.");
    }
  };

  // Función genérica para enviar la imagen (sirve para galería y webcam)
  const enviarImagen = async (fileOrBlob: Blob, isGallery = false) => {
    setEscaneando(true);
    const formData = new FormData();
    formData.append("file", fileOrBlob, "dni_captura.jpg");

    try {
      const res = await fetch(`${API_URL}/escanear`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (data.status === "success") {
        alert(`✅ Éxito: DNI ${data.datos.dni} registrado.`);
        setMostrarWebcam(false); // Cierra la cámara si fue exitoso
        cargarDatos();
      } else {
        alert(`❌ Error: ${data.message}`);
      }
    } catch (error) {
      alert("Error de conexión. Revisa que el servidor Python esté encendido.");
    } finally {
      setEscaneando(false);
      if (isGallery && galleryInputRef.current) galleryInputRef.current.value = "";
    }
  };

  // Manejador para la galería
  const handleGaleria = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) enviarImagen(file, true);
  };

  // Manejador para la Webcam integrada
  const capturarWebcam = useCallback(async () => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;

    const res = await fetch(imageSrc);
    const blob = await res.blob();
    enviarImagen(blob, false);
  }, [webcamRef]);

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Sistema KYC - UCV
            </h1>
            <p className="text-gray-400">Panel de Verificación de Identidad</p>
          </div>
          
          <div className="flex flex-wrap gap-3">
            <button 
              onClick={cargarDatos}
              className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg font-medium transition-colors border border-gray-700 flex items-center gap-2"
            >
              🔄 Actualizar
            </button>
            
            <input
  type="file"
  accept="image/*"
  ref={galleryInputRef}
  onChange={handleGaleria}
  className="hidden"
  title="Seleccionar foto de galería" 
/>

            {/* Este botón ahora activa la vista de la Webcam web en lugar de la nativa */}
            <button 
              onClick={() => setMostrarWebcam(!mostrarWebcam)}
              disabled={escaneando}
              className={`${mostrarWebcam ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"} px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 shadow-lg`}
            >
              {mostrarWebcam ? "✖ Cancelar Escáner" : "📷 Iniciar Escáner"}
            </button>

            <button 
              onClick={() => galleryInputRef.current?.click()}
              disabled={escaneando}
              className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-purple-900/20"
            >
              {escaneando ? "⏳ Procesando..." : "🖼️ Subir Foto"}
            </button>
          </div>
        </div>

        {/* VISTA DE LA CÁMARA CON LA MÁSCARA (Se muestra solo si mostrarWebcam es true) */}
        {mostrarWebcam && !escaneando && (
          <div className="mb-8 p-6 bg-gray-900 border border-gray-800 rounded-xl flex flex-col items-center">
            <div className="relative border-4 border-dashed border-gray-400 rounded-lg overflow-hidden flex justify-center items-center bg-black w-full max-w-lg">
              {/* @ts-ignore */}
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                screenshotQuality={1}
                videoConstraints={{ facingMode: "environment", // Usa la cámara trasera en celulares
                width: { ideal: 1920 },
                  height: { ideal: 1080 }
                }}
                className="w-full h-auto"
              />

              {/* OVERLAY / MÁSCARA VISUAL */}
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="relative w-[80%] h-[60%] rounded-xl shadow-[0_0_0_9999px_rgba(0,0,0,0.7)] border-2 border-green-400 flex flex-col justify-between">
                  <div className="bg-black/80 text-green-400 text-xs font-bold text-center py-2 px-1">
                    Encuadre el DNI dentro del recuadro evitando reflejos
                  </div>
                  <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-green-500 rounded-tl-xl"></div>
                  <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-green-500 rounded-tr-xl"></div>
                  <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-green-500 rounded-bl-xl"></div>
                  <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-green-500 rounded-br-xl"></div>
                </div>
              </div>
            </div>

            <button
              onClick={capturarWebcam}
              disabled={escaneando}
              className={`mt-4 px-8 py-3 rounded-lg font-bold text-white transition-all w-full max-w-lg ${
                escaneando
                  ? "bg-gray-500 cursor-not-allowed"
                  : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {escaneando ? "Procesando con YOLO..." : "🎯 Capturar y Validar"}
            </button>
          </div>
        )}

        {/* TABLA DE REGISTROS (Se oculta parcialmente si la cámara está activa para ahorrar espacio) */}
        {!mostrarWebcam && (
          loading ? (
            <div className="text-center py-10 bg-gray-900 border border-gray-800 rounded-xl">
              <p className="text-gray-400 animate-pulse">Cargando base de datos...</p>
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto shadow-2xl">
              <table className="w-full text-left text-sm min-w-[700px]">
                <thead className="bg-gray-800/50 text-gray-300">
                  <tr>
                    <th className="p-4 font-semibold">Usuario</th>
                    <th className="p-4 font-semibold">DNI</th>
                    <th className="p-4 font-semibold">Nacimiento</th>
                    <th className="p-4 font-semibold text-center">Edad</th>
                    <th className="p-4 font-semibold">Género</th>
                    <th className="p-4 font-semibold text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {registros.map((reg) => (
                    <tr key={reg._id} className="hover:bg-gray-800/30 transition-colors">
                      <td className="p-4">
                        <p className="font-medium text-white uppercase">{reg.nombres}</p>
                        <p className="text-xs text-gray-400 uppercase">{reg.apellidos}</p>
                      </td>
                      <td className="p-4 font-mono text-gray-300">
                        {reg.dni}
                      </td>
                      <td className="p-4 text-gray-400">
                        {editandoId === reg._id ? (
                          <div className="flex items-center gap-2">
                            <input
                              value={tempFecha}
                              onChange={(e) => setTempFecha(e.target.value)}
                              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white text-sm w-28"
                              placeholder="DD/MM/AAAA"
                            />
                            <button onClick={() => guardarCambio(reg._id)} className="text-green-400 hover:text-green-300 font-bold" title="Guardar">✓</button>
                            <button onClick={() => setEditandoId(null)} className="text-red-400 hover:text-red-300 font-bold" title="Cancelar">✕</button>
                          </div>
                        ) : (
                          <span
                            onClick={() => {
                              setEditandoId(reg._id);
                              setTempFecha(reg.fecha_nacimiento);
                            }}
                            className="cursor-pointer border-b border-dashed border-gray-600 hover:text-blue-300 transition-colors"
                            title="Click para editar fecha"
                          >
                            {reg.fecha_nacimiento} ✏️
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-center font-medium text-blue-400">
                        {reg.edad || "-"}
                      </td>
                      <td className="p-4 text-gray-400">{reg.genero}</td>
                      <td className="p-4 text-center">
                        <button 
                          onClick={() => eliminarRegistro(reg._id)}
                          className="text-red-400 hover:text-red-300 hover:bg-red-400/10 px-3 py-1 rounded transition-colors text-xs font-semibold"
                          title="Eliminar registro"
                        >
                          🗑️ Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                  {registros.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-10 text-center text-gray-500">
                        No hay DNIs en la base de datos.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </main>
  );
}