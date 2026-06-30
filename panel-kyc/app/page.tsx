"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import Webcam from "react-webcam"; 

interface Registro {
  _id: string;
  nombres: string;
  apellidos: string;
  dni: string;
  fecha_nacimiento: string;
  genero: string;
  edad?: string; 
}

interface EvaluacionIA {
  estado: string;
  confianza: string;
}

export default function Home() {
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [loading, setLoading] = useState(true);
  const [escaneando, setEscaneando] = useState(false);
  
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [tempFecha, setTempFecha] = useState("");

  const [mostrarWebcam, setMostrarWebcam] = useState(false);

  const [evaluaciones, setEvaluaciones] = useState<Record<string, EvaluacionIA>>({});
  const [modalRiesgo, setModalRiesgo] = useState(false);
  const [usuarioRiesgo, setUsuarioRiesgo] = useState<Registro | null>(null);
  const [formIngresos, setFormIngresos] = useState("");
  const [formIndependiente, setFormIndependiente] = useState("0"); 
  const [evaluando, setEvaluando] = useState(false);

  const galleryInputRef = useRef<HTMLInputElement>(null);
  const webcamRef = useRef<Webcam>(null);

  const API_URL = "https://jhoncgp-api-kyc.hf.space";

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
        setMostrarWebcam(false); 
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

  const handleGaleria = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) enviarImagen(file, true);
  };

  const capturarWebcam = useCallback(async () => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;

    const res = await fetch(imageSrc);
    const blob = await res.blob();
    enviarImagen(blob, false);
  }, [webcamRef]);

  const procesarEvaluacionIA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usuarioRiesgo || !usuarioRiesgo.edad) return;

    setEvaluando(true);
    const edadNumerica = parseInt(usuarioRiesgo.edad.replace(/\D/g, "")) || 18;

    try {
      const res = await fetch(`${API_URL}/evaluar-riesgo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          edad: edadNumerica,
          ingresos: parseFloat(formIngresos),
          es_independiente: parseInt(formIndependiente)
        }),
      });
      
      const data = await res.json();
      
      if (data.status === "success") {
        setEvaluaciones(prev => ({
          ...prev,
          [usuarioRiesgo._id]: {
            estado: data.resultado_ia,
            confianza: data.confianza_bayes
          }
        }));
        setModalRiesgo(false); 
        setFormIngresos(""); 
      } else {
        alert("Error de la IA: " + data.message);
      }
    } catch (error) {
      alert("Error al conectar con el modelo Naive Bayes.");
    } finally {
      setEvaluando(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Sistema KYC & Credit Scoring
            </h1>
            <p className="text-gray-400">Verificación de Identidad y Evaluación de Riesgo (IA)</p>
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
              aria-label="Subir imagen de DNI"
              title="Subir imagen de DNI"
            />

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
        
        {/* ==========================================
         SENSOR DEL AGENTE INTELIGENTE (PERCEPCIÓN)
         Captura el entorno (la imagen del DNI) para enviarlo al motor de reglas
         ========================================== */}
        {mostrarWebcam && !escaneando && (
          <div className="mb-8 p-6 bg-gray-900 border border-gray-800 rounded-xl flex flex-col items-center">
            <div className="relative border-4 border-dashed border-gray-400 rounded-lg overflow-hidden flex justify-center items-center bg-black w-full max-w-lg">
              {/* @ts-ignore */}
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                screenshotQuality={1}
                videoConstraints={{ facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } }}
                className="w-full h-auto"
              />
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="relative w-[80%] h-[60%] rounded-xl shadow-[0_0_0_9999px_rgba(0,0,0,0.7)] border-2 border-green-400 flex flex-col justify-between">
                  <div className="bg-black/80 text-green-400 text-xs font-bold text-center py-2 px-1">
                    Encuadre el DNI dentro del recuadro
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
                escaneando ? "bg-gray-500 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {escaneando ? "Procesando OCR..." : "🎯 Capturar DNI"}
            </button>
          </div>
        )}

        {!mostrarWebcam && (
          loading ? (
            <div className="text-center py-10 bg-gray-900 border border-gray-800 rounded-xl">
              <p className="text-gray-400 animate-pulse">Cargando base de datos...</p>
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto shadow-2xl">
              <table className="w-full text-left text-sm min-w-[850px]">
                <thead className="bg-gray-800/50 text-gray-300">
                  <tr>
                    <th className="p-4 font-semibold">Usuario</th>
                    <th className="p-4 font-semibold">DNI</th>
                    <th className="p-4 font-semibold text-center">Edad</th>
                    <th className="p-4 font-semibold text-center">Evaluación (IA)</th>
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
                      <td className="p-4 text-center font-medium text-blue-400">
                        {reg.edad || "-"}
                      </td>
                      
                      {/* COLUMNA NAIVE BAYES */}
                      <td className="p-4 text-center">
                        {evaluaciones[reg._id] ? (
                          <div className="flex flex-col items-center">
                            <span className={`px-3 py-1 rounded-full text-xs font-bold shadow-sm ${
                              evaluaciones[reg._id].estado === "Aprobado Automáticamente" 
                                ? "bg-green-500/20 text-green-400 border border-green-500/30" 
                                : "bg-red-500/20 text-red-400 border border-red-500/30"
                            }`}>
                              {evaluaciones[reg._id].estado}
                            </span>
                            <span className="text-[10px] text-gray-500 mt-1">
                              Precisión Naive Bayes: {evaluaciones[reg._id].confianza}
                            </span>
                          </div>
                        ) : (
                           <button 
                             onClick={() => { setUsuarioRiesgo(reg); setModalRiesgo(true); }}
                             className="text-xs bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/40 px-3 py-1.5 rounded transition-colors"
                           >
                             🧠 Evaluar Riesgo
                           </button>
                        )}
                      </td>

                      <td className="p-4 text-center flex justify-center gap-2">
                        <button 
                          onClick={() => eliminarRegistro(reg._id)}
                          className="text-gray-500 hover:text-red-400 hover:bg-red-400/10 px-2 py-1 rounded transition-colors text-lg"
                          title="Eliminar"
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))}
                  {registros.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-10 text-center text-gray-500">
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

      {/* MODAL DE FORMULARIO NAIVE BAYES */}
      {modalRiesgo && usuarioRiesgo && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 p-6 rounded-xl w-full max-w-md shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">Perfilamiento Crediticio</h3>
              <button onClick={() => setModalRiesgo(false)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <p className="text-sm text-gray-400 mb-6">
              Ingresa los datos financieros de <strong className="text-blue-400">{usuarioRiesgo.nombres}</strong>. El algoritmo Naive Bayes cruzará esto con su edad ({usuarioRiesgo.edad}) para calcular el riesgo.
            </p>

            <form onSubmit={procesarEvaluacionIA} className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Ingresos Mensuales (S/)</label>
                <input 
                  type="number" 
                  required 
                  min="0"
                  value={formIngresos}
                  onChange={(e) => setFormIngresos(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="Ej: 2500"
                />
              </div>

              <div>
                <label htmlFor="situacion-laboral" className="block text-sm font-medium text-gray-300 mb-1">Situación Laboral</label>
                <select 
                  id="situacion-laboral"
                  value={formIndependiente}
                  onChange={(e) => setFormIndependiente(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                >
                  <option value="0">Trabajador Dependiente (Planilla)</option>
                  <option value="1">Trabajador Independiente (RxH)</option>
                </select>
              </div>

              <button 
                type="submit" 
                disabled={evaluando}
                className="mt-4 w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 py-3 rounded-lg font-bold text-white transition-all shadow-lg shadow-blue-900/30 flex justify-center items-center gap-2"
              >
                {evaluando ? "Calculando Probabilidad..." : "🤖 Ejecutar Modelo IA"}
              </button>
            </form>
          </div>
        </div>
      )}

    </main>
  );
}