const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const QRCode = require('qrcode');
const http = require('http');
const path = require('path');
const fs = require('fs');

const API_ENDPOINT = process.env.API_ENDPOINT || 'https://ikiam-academic-chatbot.onrender.com/api/chat';
const PORT = process.env.PORT || 3001;
const ARTIFACT_DIR = process.env.ARTIFACT_DIR || 'C:\\Users\\Armandd\\.gemini\\antigravity\\brain\\62d76324-c613-4dfd-bb56-531ce8134209';

let currentQRDataUrl = null;
let connectionState = 'Iniciando...';
let connectedUser = null;

// Mapa de sesión en memoria: remoteJid -> { scope, sid, waitingHuman }
const userSessions = new Map();

// Servidor HTTP simple para ver el código QR en el navegador
const server = http.createServer((req, res) => {
  if (req.url === '/qr.png' && currentQRDataUrl) {
    const base64Data = currentQRDataUrl.replace(/^data:image\/png;base64,/, '');
    const img = Buffer.from(base64Data, 'base64');
    res.writeHead(200, { 'Content-Type': 'image/png', 'Content-Length': img.length });
    res.end(img);
    return;
  }

  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(`
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="utf-8">
      <title>WhatsApp Bot — Ikiam</title>
      <meta http-equiv="refresh" content="5">
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 40px 20px; background: #f8fafc; color: #1e293b; margin: 0; }
        .card { max-width: 440px; margin: 0 auto; background: white; padding: 32px 24px; border-radius: 12px; box-shadow: 0 4px 14px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }
        h1 { font-size: 20px; color: #0d5f3a; margin-top: 0; margin-bottom: 8px; }
        p { font-size: 13px; color: #64748b; line-height: 1.5; margin: 8px 0; }
        .status { font-weight: 700; padding: 6px 14px; border-radius: 20px; display: inline-block; font-size: 12px; margin: 12px 0 16px; background: #e2e8f0; }
        .connected { background: #dcfce7; color: #166534; }
        .waiting { background: #fef3c7; color: #92400e; }
        img { width: 260px; height: 260px; margin: 14px auto; display: block; border: 1px solid #cbd5e1; border-radius: 8px; }
        ol { text-align: left; font-size: 12.5px; color: #475569; line-height: 1.6; margin: 16px 0; padding-left: 20px; }
        .footer { font-size: 11px; color: #94a3b8; margin-top: 20px; }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>Vinculación WhatsApp Ikiam</h1>
        <div class="status ${connectionState === 'Conectado' ? 'connected' : 'waiting'}">Estado: ${connectionState}</div>
        ${connectedUser ? `<p><strong>Número bot activo:</strong> +${connectedUser.split(':')[0]}</p>` : ''}
        ${currentQRDataUrl && connectionState !== 'Conectado' ? `
          <p>Abra WhatsApp en su teléfono móvil y escanee este código:</p>
          <img src="/qr.png" alt="Código QR WhatsApp" />
          <ol>
            <li>En su teléfono abra <strong>WhatsApp</strong>.</li>
            <li>Vaya a <strong>Ajustes / Configuración</strong> o menú de 3 puntos.</li>
            <li>Seleccione <strong>Dispositivos vinculados</strong>.</li>
            <li>Presione <strong>Vincular un dispositivo</strong> y enfoque esta pantalla.</li>
          </ol>
        ` : (connectionState === 'Conectado' ? '<p style="color:#166534; font-weight:600;">El bot está en línea y responderá automáticamente a los mensajes entrantes.</p>' : '<p>Generando código QR seguro...</p>')}
        <div class="footer">Ikiam Academic Chatbot — Gateway V2.5</div>
      </div>
    </body>
    </html>
  `);
});

server.listen(PORT, () => {
  console.log(`[HTTP] Panel de vinculación QR activo en: http://localhost:${PORT}`);
});

function limpiarHtmlParaWhatsApp(texto) {
  if (!texto) return '';
  return texto
    // Eliminar mailto: enlaces tipo [correo](mailto:correo) o <a href="mailto:...">correo</a>
    .replace(/\[([^\]]+)\]\(mailto:[^)]+\)/gi, '$1')
    .replace(/<a[^>]*href=['"]mailto:([^'"]+)['"][^>]*>(.*?)<\/a>/gi, '$1')
    .replace(/\(mailto:[^)]+\)/gi, '')
    // Reemplazar enlaces relativos a documentos por URLs absolutas en producción
    .replace(/\[Visualizar PDF:\s*Visualizar PDF:\s*([^\]]+)\]\(([^)]+)\)/gi, 'Visualizar PDF: $1 (https://ikiam-academic-chatbot.onrender.com$2)')
    .replace(/\[Visualizar PDF:\s*([^\]]+)\]\(([^)]+)\)/gi, 'Visualizar PDF: $1 (https://ikiam-academic-chatbot.onrender.com$2)')
    .replace(/\[Descargar Formato:\s*Descargar Formato:\s*([^\]]+)\]\(([^)]+)\)/gi, 'Descargar Formato: $1 (https://ikiam-academic-chatbot.onrender.com$2)')
    .replace(/\[Descargar Formato:\s*([^\]]+)\]\(([^)]+)\)/gi, 'Descargar Formato: $1 (https://ikiam-academic-chatbot.onrender.com$2)')
    .replace(/\[([^\]]+)\]\((\/documentos\/[^)]+)\)/gi, '$1 (https://ikiam-academic-chatbot.onrender.com$2)')
    // HTML básicos
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<strong>(.*?)<\/strong>/gi, '*$1*')
    .replace(/<b>(.*?)<\/b>/gi, '*$1*')
    .replace(/<em>(.*?)<\/em>/gi, '_$1_')
    .replace(/<i>(.*?)<\/i>/gi, '_$1_')
    .replace(/<div[^>]*>(.*?)<\/div>/gi, '\n$1\n')
    .replace(/<p[^>]*>(.*?)<\/p>/gi, '\n$1\n')
    .replace(/<a[^>]*href=['"]([^'"]+)['"][^>]*>(.*?)<\/a>/gi, '$2 ($1)')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    // Separar viñetas o autoridades pegadas
    .replace(/\)\*([A-Za-z0-9])/g, ')\n• *$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function consultarMotorIkiam(texto, senderId, scope, sessionId) {
  try {
    const res = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: texto,
        sessionId: sessionId || `wa_${senderId}`,
        clientId: `wa_${senderId}`,
        scope: scope || 'academico'
      })
    });
    const data = await res.json();
    return data.reply ? limpiarHtmlParaWhatsApp(data.reply) : 'Disculpe, no se pudo procesar la consulta en este momento.';
  } catch (err) {
    console.error('[API ERROR]', err.message);
    return 'Ocurrió un error temporal al consultar el repositorio académico de Ikiam. Por favor reintente en unos instantes.';
  }
}

async function iniciarBotWhatsApp() {
  const authDir = path.join(__dirname, 'auth_info');
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    logger: pino({ level: 'silent' }),
    printQRInTerminal: true,
    auth: state,
    browser: ['Ikiam Academic Chatbot', 'Chrome', '1.0.0']
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      connectionState = 'Esperando escaneo de QR';
      currentQRDataUrl = await QRCode.toDataURL(qr, { scale: 8 });
      console.log('\n======================================================');
      console.log('CÓDIGO QR GENERADO. Abra en su navegador:');
      console.log(`>>> http://localhost:${PORT}`);
      console.log('======================================================\n');

      try {
        const base64Data = currentQRDataUrl.replace(/^data:image\/png;base64,/, '');
        const buffer = Buffer.from(base64Data, 'base64');
        fs.writeFileSync(path.join(__dirname, 'qr_whatsapp.png'), buffer);
        if (fs.existsSync(ARTIFACT_DIR)) {
          fs.writeFileSync(path.join(ARTIFACT_DIR, 'qr_whatsapp.png'), buffer);
        }
      } catch (e) {
        console.error('Error guardando qr_whatsapp.png:', e.message);
      }
    }

    if (connection === 'close') {
      const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
      connectionState = 'Desconectado';
      console.log('[CONEXIÓN] Sesión cerrada. Reconectando:', shouldReconnect);
      if (shouldReconnect) {
        setTimeout(iniciarBotWhatsApp, 3000);
      }
    } else if (connection === 'open') {
      connectionState = 'Conectado';
      connectedUser = sock.user?.id || 'Desconocido';
      currentQRDataUrl = null;
      console.log('\n======================================================');
      console.log('BOT DE WHATSAPP CONECTADO EXITOSAMENTE');
      console.log('Número asignado como bot:', connectedUser);
      console.log('Listo para atender mensajes entrantes.');
      console.log('======================================================\n');
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;

      const remoteJid = msg.key.remoteJid;
      if (!remoteJid || remoteJid.includes('@broadcast') || remoteJid.includes('@newsletter')) continue;

      const rawText = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
      const texto = rawText.trim();
      if (!texto) continue;

      const senderNum = remoteJid.replace('@s.whatsapp.net', '').replace('@lid', '');
      console.log(`[IN] Mensaje recibido de ${senderNum}: "${texto}"`);

      let session = userSessions.get(remoteJid);
      if (!session) {
        session = {
          scope: 'academico',
          sid: `wa_${senderNum}_${Date.now()}`,
          waitingHuman: false
        };
        userSessions.set(remoteJid, session);
      }

      const cmd = texto.toLowerCase();

      // 1. Detección de reactivación si el bot estaba pausado por asesor humano
      const esReactivacion = ['bot', '/bot', 'menu', '0', 'reiniciar', 'reset', 'activar bot'].includes(cmd);
      if (session.waitingHuman && !esReactivacion) {
        console.log(`[HUMANO ACTIVO] Ignorando respuesta automática para ${senderNum} (en atención personalizada).`);
        continue;
      }
      if (session.waitingHuman && esReactivacion) {
        session.waitingHuman = false;
        userSessions.set(remoteJid, session);
      }

      // 2. Comandos de reinicio explícito (Siempre disponibles)
      const esReinicio = ['0', 'reiniciar', 'reset', '/reset', '/reiniciar', 'nuevo', 'nuevo chat', 'nueva consulta', 'borrar', 'limpiar', 'empezar de nuevo'].includes(cmd);
      if (esReinicio) {
        session = {
          scope: 'academico',
          sid: `wa_${senderNum}_${Date.now()}`,
          waitingHuman: false
        };
        userSessions.set(remoteJid, session);
        await sock.sendMessage(remoteJid, {
          text: '*Chat reiniciado con éxito.*\nSe ha borrado el historial de la conversación.\nPuede iniciar una nueva consulta o escribir *menu* para ver las opciones disponibles.'
        });
        continue;
      }

      // Saludos naturales: responder brevemente, directo y amigable (sin PDFs ni monólogos corporativos)
      const saludosRegex = /^(hola|hola\s+como\s+estas|hola\s+que\s+tal|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|que\s+tal|buenas|saludos|hey|ola)[\s.?!]*$/i;
      if (saludosRegex.test(cmd)) {
        const saludoText = [
          '¡Hola! Bienvenido/a al canal de WhatsApp de la Universidad Regional Amazónica Ikiam.',
          'Soy tu guía virtual. ¿En qué puedo ayudarte hoy?',
          '',
          'Puedes escribir tu consulta directamente o enviar *menu* para ver las opciones principales.',
          '',
          '---',
          '_Escribe *menu* para opciones, *guia* para atención personalizada, o *0* para reiniciar._'
        ].join('\n');
        await sock.sendMessage(remoteJid, { text: saludoText });
        continue;
      }

      // Detección de consultas de ubicación / mapa de Ikiam
      const esUbicacion = ['donde queda', 'dónde queda', 'ubicacion', 'ubicación', 'donde esta', 'dónde está', 'direccion', 'dirección', 'como llegar', 'cómo llegar', 'mapa'].some(k => cmd.includes(k));
      if (esUbicacion) {
        const ubicacionText = [
          '*Ubicación de la Universidad Regional Amazónica Ikiam:*',
          'El campus matriz se encuentra ubicado en:',
          'Km 7 Vía a Muyuna, Parroquia Muyuna, Cantón Tena, Provincia de Napo, Ecuador.',
          '',
          '*Enlace de Google Maps:*',
          'https://maps.google.com/?q=Universidad+Regional+Amazonica+Ikiam',
          '',
          'Todas nuestras carreras de pregrado se imparten en modalidad *100% presencial* en este campus.',
          '',
          '---',
          '_Escribe *menu* para opciones, *guia* para atención personalizada, o *0* para reiniciar._'
        ].join('\n');
        await sock.sendMessage(remoteJid, { text: ubicacionText });
        continue;
      }

      // Detección de carrera aislada (cuando solo envían el nombre sin preguntar nada)
      const carrerasMap = {
        'biotecnologia': { nombre: 'Ingeniería en Biotecnología', facultad: 'Facultad de Ciencias de la Vida (FCV)', puntaje: '760 pts (referencial 1PA 2027)' },
        'geociencias': { nombre: 'Ingeniería en Geociencias', facultad: 'Facultad de Ciencias de la Tierra y Agua (FCTA)', puntaje: '745 pts (referencial 1PA 2027)' },
        'hidrologia': { nombre: 'Ingeniería en Hidrología', facultad: 'Facultad de Ciencias de la Tierra y Agua (FCTA)', puntaje: '740 pts (referencial 1PA 2027)' },
        'agroecologia': { nombre: 'Ingeniería en Agroecología', facultad: 'Facultad de Ciencias de la Tierra y Agua (FCTA)', puntaje: '750 pts (referencial 1PA 2027)' },
        'electromecanica': { nombre: 'Ingeniería en Electromecánica y Energías Renovables', facultad: 'Facultad de Ciencias de la Tierra y Agua (FCTA)', puntaje: '770 pts (referencial 1PA 2027)' },
        'ecosistemas': { nombre: 'Ingeniería en Ecosistemas', facultad: 'Facultad de Ciencias de la Vida (FCV)', puntaje: '755 pts (referencial 1PA 2027)' },
        'veterinaria': { nombre: 'Medicina Veterinaria y Manejo de Vida Silvestre', facultad: 'Facultad de Ciencias de la Vida (FCV)', puntaje: '865 pts (referencial 1PA 2027)' },
        'medicina veterinaria': { nombre: 'Medicina Veterinaria y Manejo de Vida Silvestre', facultad: 'Facultad de Ciencias de la Vida (FCV)', puntaje: '865 pts (referencial 1PA 2027)' },
        'biocomercio': { nombre: 'Licenciatura en Biocomercio', facultad: 'Facultad de Ciencias Socioambientales (FCSA)', puntaje: '735 pts (referencial 1PA 2027)' },
        'arquitectura': { nombre: 'Arquitectura Sostenible', facultad: 'Facultad de Ciencias Socioambientales (FCSA)', puntaje: '800 pts (referencial 1PA 2027)' },
        'ciencias experimentales': { nombre: 'Educación en Ciencias Experimentales', facultad: 'Facultad de Ciencias Socioambientales (FCSA)', puntaje: '725 pts (referencial 1PA 2027)' }
      };

      const normCarrera = cmd.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z\s]/g, '').trim();
      if (carrerasMap[normCarrera]) {
        const cInfo = carrerasMap[normCarrera];
        const respCarrera = [
          `*${cInfo.nombre}*`,
          `Pertenece a la *${cInfo.facultad}*.`,
          `Puntaje referencial de ingreso: *${cInfo.puntaje}*.`,
          '',
          '¿Qué información específica necesitas?',
          '• Requisitos, examen y fechas de admisión 1PA 2027',
          '• Malla curricular y perfil profesional',
          '• Trámites académicos (estudiantes regulares)',
          '',
          'Escribe tu pregunta o envía *menu* para ver las opciones disponibles.',
          '',
          '---',
          '_Escribe *menu* para opciones, *guia* para atención personalizada, o *0* para reiniciar._'
        ].join('\n');
        await sock.sendMessage(remoteJid, { text: respCarrera });
        continue;
      }

      // 3. Opción de contactar con un guía humano (Atención personalizada)
      const esContactoGuia = ['6', 'guia', '/guia', 'asesor', '/asesor', 'humano', 'persona', 'contacto', 'agente', 'guia humano', 'atencion personalizada'].includes(cmd);
      if (esContactoGuia) {
        session.waitingHuman = true;
        userSessions.set(remoteJid, session);
        console.log(`[ALERTA GUÍA] El usuario ${senderNum} solicitó atención personalizada con un guía humano.`);
        const guiaText = [
          '*Solicitud de Atención con Guía Humano*',
          'Su solicitud ha sido registrada para atención personalizada por el equipo de guías de Ikiam.',
          '',
          '*Canales Oficiales Directos:*',
          '• *Admisiones e Ingreso:* admisiones@ikiam.edu.ec',
          '• *Dirección Académica y Trámites:* direccion.academica@ikiam.edu.ec',
          '• *Teléfono de atención:* +593 99 561 6311',
          '• *Horario de atención:* Lunes a viernes de 08h00 a 17h00.',
          '',
          'Un guía humano atenderá su consulta directamente en este chat. El asistente virtual automático queda pausado para no interferir.',
          '',
          '_Si en cualquier momento desea reactivar el asistente virtual automático, escriba *bot* o *0*._'
        ].join('\n');

        await sock.sendMessage(remoteJid, { text: guiaText });
        continue;
      }

      // 4. Menú principal estructurado
      if (cmd === '/menu' || cmd === 'menu' || cmd === 'ayuda' || cmd === '/ayuda' || cmd === 'hola') {
        const menuText = [
          '*Ikiam — Guía Académico y Admisiones*',
          'Bienvenido/a al canal de atención de la Universidad Regional Amazónica Ikiam.',
          '',
          '*1.* Admisiones 1PA 2027 (Carreras, requisitos, fechas y puntajes)',
          '*2.* Procesos Académicos (Trámites, justificaciones, retiros y matrículas)',
          '*3.* Formatos y Solicitudes Oficiales descargables',
          '*4.* Justificación de Inasistencias (Art. 87 RRA)',
          '*5.* Retiro Extraordinario de Asignaturas',
          '*6.* Contactar con un Guía Humano (Atención personalizada)',
          '*0.* Reiniciar chat / Borrar historial (/reset)',
          '',
          'Responda con el *número* deseado o escriba su consulta directamente.'
        ].join('\n');

        await sock.sendMessage(remoteJid, { text: menuText });
        continue;
      }

      // 5. Opciones del menú
      if (cmd === '/admision' || cmd === '1') {
        session.scope = 'admisiones';
        userSessions.set(remoteJid, session);
        await sock.sendMessage(remoteJid, {
          text: '*Modo Admisiones Ikiam (1PA 2027) activado.*\nPuede consultar sobre requisitos de ingreso, oferta de carreras, fechas del proceso o puntajes referenciales.\n\n_Escriba *0* para reiniciar o *menu* para ver opciones._'
        });
        continue;
      }

      if (cmd === '/academico' || cmd === '2') {
        session.scope = 'academico';
        userSessions.set(remoteJid, session);
        await sock.sendMessage(remoteJid, {
          text: '*Modo Procesos Académicos activado.*\nPuede consultar sobre trámites, homologaciones, retiros de asignaturas o justificaciones de inasistencia.\n\n_Escriba *0* para reiniciar o *menu* para ver opciones._'
        });
        continue;
      }

      if (cmd === '3') {
        const respuesta = await consultarMotorIkiam('¿Dónde descargo los formatos oficiales de solicitud de la Dirección Académica?', senderNum, 'academico', session.sid);
        await sock.sendMessage(remoteJid, { text: respuesta + '\n\n---\n_Escribe *menu* para opciones, *guia* para ayuda humana, o *0* para reiniciar._' });
        continue;
      }

      if (cmd === '4') {
        const respuesta = await consultarMotorIkiam('caso:justificacion_salud', senderNum, 'academico', session.sid);
        await sock.sendMessage(remoteJid, { text: respuesta + '\n\n---\n_Escribe *menu* para opciones, *guia* para ayuda humana, o *0* para reiniciar._' });
        continue;
      }

      if (cmd === '5') {
        const respuesta = await consultarMotorIkiam('caso:retiro_asignaturas_extraordinario', senderNum, 'academico', session.sid);
        await sock.sendMessage(remoteJid, { text: respuesta + '\n\n---\n_Escribe *menu* para opciones, *guia* para ayuda humana, o *0* para reiniciar._' });
        continue;
      }

      // 6. Detección inteligente automática de ámbito para preguntas libres
      const esAcademico = [
        'matricula', 'tercera matricula', 'inasistencia', 'falta medica', 'justificar', 'retiro',
        'homologacion', 'reingreso', 'rra', 'reglamento', 'pao', 'examen atrasado', 'sancion'
      ].some(k => cmd.includes(k));

      const esAdmision = [
        'como ingresar', 'inscribirme', 'inscripcion', 'senescyt', 'examen de admision', 'simulador',
        'oferta de carreras', 'carreras que ofrece', 'que carreras hay', 'puntaje referencial', 'costo de carrera',
        'ingresar a ikiam'
      ].some(k => cmd.includes(k));

      if (esAcademico && session.scope !== 'academico') {
        session.scope = 'academico';
        console.log(`[AUTO-SCOPE] Cambio dinámico a 'academico' por detección de término.`);
      } else if (esAdmision && session.scope !== 'admisiones') {
        session.scope = 'admisiones';
        console.log(`[AUTO-SCOPE] Cambio dinámico a 'admisiones' por detección de término.`);
      }

      // 7. Consulta abierta al motor RAG de Ikiam
      console.log(`[PROCESANDO] Enviando a Render (${session.scope}) | SID: ${session.sid}...`);
      const respuesta = await consultarMotorIkiam(texto, senderNum, session.scope, session.sid);
      console.log(`[OUT] Respondiendo a ${senderNum}...`);

      const footer = '\n\n---\n_Escribe *menu* para opciones, *guia* para atención personalizada, o *0* para reiniciar el chat._';
      await sock.sendMessage(remoteJid, { text: respuesta + footer });
    }
  });
}

iniciarBotWhatsApp().catch(err => {
  console.error('[FATAL ERROR INICIALIZANDO BAILEYS]', err);
});
