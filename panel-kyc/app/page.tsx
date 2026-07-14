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
  estado_bayes: string;
  confianza_bayes: string;
  estado_red_neuronal: string;
  neta_calculada: number;
}

export default function Home() {
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [loading, setLoading] = useState(true);
  const [escaneando, setEscaneando] = useState(false);
  
  // Estados para corrección manual de edad
  const [editandoEdadId, setEditandoEdadId] = useState<string | null>(null);
  const [tempEdad, setTempEdad] = useState("");

  const [mostrarWebcam, setMostrarWebcam] = useState(false);

  const [evaluaciones, setEvaluaciones] = useState<Record<string, EvaluacionIA>>({});
  const [modalRiesgo, setModalRiesgo] = useState(false);
  const [usuarioRiesgo, setUsuarioRiesgo] = useState<Registro | null>(null);
  
  // Estados del Formulario (Ahora incluye Deuda)
  const [formIngresos, setFormIngresos] = useState("");
  const [formDeuda, setFormDeuda] = useState("");
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

  // Función adaptada para corregir la edad manualmente si el OCR falla
  const guardarEdadManual = async (id: string, dni: string) => {
    if (!tempEdad) return;
    try {
      // Como el API actualiza fecha, mandamos una fecha ficticia que dé esa edad, o 
      // idealmente deberías ajustar tu endpoint /actualizar para aceptar la edad directa.
      // Por ahora actualizamos el estado local para la demo:
      const nuevosRegistros = registros.map(reg => {
        if(reg._id === id) {
          return { ...reg, edad: `${tempEdad} años` };
        }
        return reg;
      });
      setRegistros(nuevosRegistros);
      setEditandoEdadId(null);
      setTempEdad("");
      alert("Edad corregida localmente para la evaluación IA.");
    } catch (error) {
      alert("Error al corregir la edad.");
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

    // Validación de seguridad para que la IA no reciba texto
    if (usuarioRiesgo.edad.includes("No calculada") || usuarioRiesgo.edad.includes("Error")) {
      alert("Debes corregir la edad manualmente antes de evaluar.");
      return;
    }

    setEvaluando(true);
    const edadNumerica = parseInt(usuarioRiesgo.edad.replace(/\D/g, "")) || 18;
    const ingresosNumericos = parseFloat(formIngresos);
    const deudaNumerica = parseFloat(formDeuda) || 0;

    try {
      // 1. Petición a Naive Bayes
      const resBayes = await fetch(`${API_URL}/evaluar-riesgo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          edad: edadNumerica,
          ingresos: ingresosNumericos,
          es_independiente: parseInt(formIndependiente)
        }),
      });
      const dataBayes = await resBayes.json();

      // 2. Petición a la Red Neuronal (Perceptrón)
      const resRedNeuronal = await fetch(`${API_URL}/evaluar-kyc-red-neuronal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ingreso_mensual: ingresosNumericos,
          deuda_actual: deudaNumerica,
          edad: edadNumerica,
          similitud_dni: 0.98 // Mock de seguridad biométrica
        }),
      });
      const dataRedNeuronal = await resRedNeuronal.json();
      
      if (dataBayes.status === "success" && dataRedNeuronal.status === "success") {
        setEvaluaciones(prev => ({
          ...prev,
          [usuarioRiesgo._id]: {
            estado_bayes: dataBayes.resultado_ia,
            confianza_bayes: dataBayes.confianza_bayes,
            estado_red_neuronal: dataRedNeuronal.decision_final,
            neta_calculada: dataRedNeuronal.matematica.funcion_neta_calculada
          }
        }));
        setModalRiesgo(false); 
        setFormIngresos(""); 
        setFormDeuda("");
      } else {
        alert("Error en uno de los modelos de IA.");
      }
    } catch (error) {
      alert("Error al conectar con los modelos de inteligencia artificial.");
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
            <p className="text-gray-400">Motor Dual: Redes Neuronales & Bayes</p>
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
                    <th className="p-4 font-semibold text-center">Evaluación Multi-Modelo (IA)</th>
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
                      <td className="p-4 text-center font-medium">
                        {/* VALIDACIÓN DE EDAD Y CORRECCIÓN MANUAL */}
                        {editandoEdadId === reg._id ? (
                           <div className="flex gap-2 justify-center">
                             <input 
                               type="number" 
                               value={tempEdad}
                               onChange={(e) => setTempEdad(e.target.value)}
                               placeholder="Edad" 
                               className="w-16 bg-gray-700 rounded px-2 text-center"
                             />
                             <button onClick={() => guardarEdadManual(reg._id, reg.dni)} className="text-green-400 hover:text-green-300">✓</button>
                           </div>
                        ) : (
                          reg.edad?.includes("No calculada") || reg.edad?.includes("Error") ? (
                            <button 
                              onClick={() => setEditandoEdadId(reg._id)}
                              className="text-xs bg-orange-500/20 text-orange-400 border border-orange-500/50 px-2 py-1 rounded shadow-sm hover:bg-orange-500/30"
                            >
                              ⚠️ Ingresar Manual
                            </button>
                          ) : (
                            <span className="text-blue-400">{reg.edad}</span>
                          )
                        )}
                      </td>
                      
                      {/* COLUMNA DUAL IA */}
                      <td className="p-4 text-center">
                        {evaluaciones[reg._id] ? (
                          <div className="flex flex-col gap-2 items-center">
                            {/* Chip Naive Bayes */}
                            <div className={`px-3 py-1 rounded-full text-[11px] font-bold shadow-sm w-full max-w-[250px] ${
                              evaluaciones[reg._id].estado_bayes === "Aprobado Automáticamente" 
                                ? "bg-green-500/10 text-green-400 border border-green-500/30" 
                                : "bg-orange-500/10 text-orange-400 border border-orange-500/30"
                            }`}>
                              Bayes: {evaluaciones[reg._id].confianza_bayes} - {evaluaciones[reg._id].estado_bayes === "Aprobado Automáticamente" ? "Aprobado" : "Revisión"}
                            </div>
                            
                            {/* Chip Red Neuronal */}
                            <div className={`px-3 py-1 rounded-full text-[11px] font-bold shadow-sm w-full max-w-[250px] ${
                              evaluaciones[reg._id].neta_calculada >= 0
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" 
                                : "bg-red-500/20 text-red-400 border border-red-500/40"
                            }`}>
                              Perceptrón: Net={evaluaciones[reg._id].neta_calculada} - {evaluaciones[reg._id].neta_calculada >= 0 ? "Aprobado" : "Fraude/Riesgo"}
                            </div>
                          </div>
                        ) : (
                           <button 
                             onClick={() => { 
                               if(reg.edad?.includes("No calculada") || reg.edad?.includes("Error")) {
                                 alert("Corrige la edad manualmente primero.");
                                 return;
                               }
                               setUsuarioRiesgo(reg); 
                               setModalRiesgo(true); 
                             }}
                             className="text-xs bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/40 px-3 py-1.5 rounded transition-colors flex items-center gap-2 mx-auto"
                           >
                             🧠 Evaluar Motores IA
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

      {/* MODAL DE FORMULARIO COMBINADO (BAYES + RED NEURONAL) */}
      {modalRiesgo && usuarioRiesgo && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 p-6 rounded-xl w-full max-w-md shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">Evaluación Multi-Modelo</h3>
              <button onClick={() => setModalRiesgo(false)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            
            <p className="text-xs text-gray-400 mb-6">
              Evaluando a <strong className="text-blue-400">{usuarioRiesgo.nombres}</strong> ({usuarioRiesgo.edad}).<br/>
              <span className="text-indigo-400 border-b border-indigo-400/30 pb-1 inline-block mt-2">Naive Bayes:</span> Analizará Ingresos y Situación.<br/>
              <span className="text-emerald-400 border-b border-emerald-400/30 pb-1 inline-block mt-1">Red Neuronal:</span> Analizará Ingresos, Deuda y Similitud DNI.
            </p>

            <form onSubmit={procesarEvaluacionIA} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Ingreso (S/)</label>
                  <input 
                    type="number" 
                    required 
                    min="0"
                    value={formIngresos}
                    onChange={(e) => setFormIngresos(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors text-sm"
                    placeholder="Ej: 2500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-emerald-400 mb-1">Deuda (S/)</label>
                  <input 
                    type="number" 
                    required 
                    min="0"
                    value={formDeuda}
                    onChange={(e) => setFormDeuda(e.target.value)}
                    className="w-full bg-gray-800 border border-emerald-600/50 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                    placeholder="Ej: 800"
                  />
                </div>
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
                className="mt-4 w-full bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 py-3 rounded-lg font-bold text-white transition-all shadow-lg shadow-emerald-900/30 flex justify-center items-center gap-2"
              >
                {evaluando ? "Ejecutando Modelos..." : "🧠 Disparar Inteligencia Artificial"}
              </button>
            </form>
          </div>
        </div>
      )}

    </main>
  );
}