"use client";
import { useEffect, useState, useRef } from "react";

interface Registro {
  _id: string;
  nombres: string;
  apellidos: string;
  dni: string;
  digito_verificador: string;
  fecha_nacimiento: string;
  estado: string;

  agencia: string;
}

export default function Home() {
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [loading, setLoading] = useState(true);
  const [escaneando, setEscaneando] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // LA IP FIJA DE TU LAPTOP: Esto es lo más seguro para que el celular la encuentre
// Borra la línea que tenías y pega esta:
// LA URL DE TU API EN LA NUBE
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

  const handleEscanear = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setEscaneando(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/escanear`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (data.status === "success") {
        alert(`✅ Éxito: DNI ${data.datos.dni} registrado.`);
        cargarDatos();
      } else {
        alert("❌ No se detectó un DNI válido. Intenta con otra foto.");
      }
    } catch (error) {
      console.error(error);
      alert("Error de conexión. Revisa que el servidor Python esté encendido.");
    } finally {
      setEscaneando(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Sistema KYC - UCV
            </h1>
            <p className="text-gray-400">Panel de Verificación KYC</p>
          </div>
          
          <div className="flex gap-3">
            <button 
              onClick={cargarDatos}
              className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg font-medium transition-colors border border-gray-700"
            >
              🔄 Actualizar
            </button>
            
            <input
              type="file"
              accept="image/*"
              ref={fileInputRef}
              onChange={handleEscanear}
              className="hidden"
              title="Subir o tomar foto del DNI"
            />
            <button 
              onClick={() => fileInputRef.current?.click()}
              disabled={escaneando}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-blue-900/20"
            >
              {escaneando ? "🧠 Procesando..." : "📷 Escanear DNI"}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-10 bg-gray-900 border border-gray-800 rounded-xl">
            <p className="text-gray-400 animate-pulse">Cargando base de datos...</p>
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto shadow-2xl">
            <table className="w-full text-left text-sm min-w-[600px]">
              <thead className="bg-gray-800/50 text-gray-300">
                <tr>
                  <th className="p-4 font-semibold">Usuario</th>
                  <th className="p-4 font-semibold">DNI</th>
                  <th className="p-4 font-semibold">Nacimiento</th>
                  <th className="p-4 font-semibold">Estado</th>
                  <th className="p-4 font-semibold text-right">Agencia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {registros.map((reg) => (
                  <tr key={reg._id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="p-4">
                      <p className="font-medium text-white">{reg.nombres}</p>
                      <p className="text-xs text-gray-400">{reg.apellidos}</p>
                    </td>
                    <td className="p-4 font-mono text-gray-300">
                      {reg.dni}-{reg.digito_verificador}
                    </td>
                    <td className="p-4 text-gray-400">{reg.fecha_nacimiento}</td>
                    <td className="p-4">
                      <span className="px-2 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full text-xs">
                        {reg.estado}
                      </span>
                    </td>
                    <td className="p-4 text-gray-500 text-xs text-right font-medium">
                      {reg.agencia}
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
        )}
      </div>
    </main>
  );
}