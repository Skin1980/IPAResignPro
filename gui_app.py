#!/usr/bin/env python3
"""
IPAResignPro - GUI Web/Local App with 1-Click Device Detection & Direct iOS Installation.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request, send_file

from resign_engine import (
    find_provisioning_profiles,
    find_signing_identities,
    resign_ipa
)

app = Flask(__name__)
STORAGE_DIR = Path.home() / "Library" / "Application Support" / "IPAResignPro"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPAResign Pro - Sideload & Install Studio</title>
    <style>
        :root {
            --bg: #0f172a;
            --surface: #1e293b;
            --primary: #0284c7;
            --primary-hover: #0369a1;
            --accent: #10b981;
            --accent-hover: #059669;
            --purple: #8b5cf6;
            --purple-hover: #7c3aed;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #475569;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 22px; min-height: 100vh; }
        .container { max-width: 920px; margin: 0 auto; }

        header { text-align: center; margin-bottom: 24px; }
        h1 { font-size: 2.1rem; color: #38bdf8; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .subtitle { color: var(--text-muted); font-size: 0.95rem; margin-top: 5px; }

        .card { background: var(--surface); border-radius: 14px; padding: 22px; border: 1px solid var(--border); margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .card h2 { font-size: 1.15rem; color: #38bdf8; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }

        .form-group { margin-bottom: 15px; }
        label { display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px; color: #cbd5e1; }
        select, input[type="text"], input[type="file"] {
            width: 100%; padding: 11px; border-radius: 8px; border: 1px solid var(--border); background: #090d16; color: white; font-size: 0.92rem;
        }

        button.btn-primary {
            width: 100%; padding: 13px; background: var(--primary); border: none; border-radius: 8px; color: white; font-size: 1rem; font-weight: 700; cursor: pointer; transition: 0.2s; margin-top: 8px;
        }
        button.btn-primary:hover { background: var(--primary-hover); }
        button.btn-install {
            width: 100%; padding: 14px; background: var(--purple); border: none; border-radius: 8px; color: white; font-size: 1.05rem; font-weight: 700; cursor: pointer; transition: 0.2s; margin-top: 12px; display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        button.btn-install:hover { background: var(--purple-hover); }
        button.btn-accent {
            width: 100%; padding: 12px; background: var(--accent); border: none; border-radius: 8px; color: white; font-size: 0.95rem; font-weight: 600; cursor: pointer; margin-top: 10px;
        }

        .badge-online { background: #059669; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .terminal-box {
            background: #050811; border: 1px solid #334155; border-radius: 8px; padding: 14px; font-family: "SF Mono", Menlo, monospace; font-size: 0.85rem; color: #38bdf8; max-height: 280px; overflow-y: auto; white-space: pre-wrap; margin-top: 14px;
        }

        .info-tip { background: rgba(2, 132, 199, 0.12); border-left: 4px solid var(--primary); padding: 10px 14px; border-radius: 6px; font-size: 0.85rem; line-height: 1.4; margin-top: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📲 IPAResign Pro <span>+ 1-Click Install</span></h1>
            <p class="subtitle">Ri-firma profonda e installazione diretta su iPhone/iPad collegati via cavo o Wi-Fi</p>
        </header>

        <div class="card">
            <h2>1. Dispositivo Apple Collegato
                <button id="btnRefreshDevices" style="background:#334155;border:none;color:white;padding:4px 12px;border-radius:6px;font-size:0.8rem;cursor:pointer;">🔄 Aggiorna</button>
            </h2>
            <div class="form-group">
                <label>Seleziona il dispositivo di destinazione:</label>
                <select id="deviceSelect">
                    <option value="">Ricerca dispositivi in corso...</option>
                </select>
            </div>
        </div>

        <div class="card">
            <h2>2. Credenziali Sviluppatore Xcode</h2>
            <div class="form-group">
                <label>Certificato di Firma:</label>
                <select id="certSelect">
                    <option value="">Caricamento certificati...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Provisioning Profile:</label>
                <select id="profileSelect">
                    <option value="">Caricamento profili...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Bundle ID (opzionale):</label>
                <input type="text" id="customBundleId" placeholder="Lascia vuoto per usare il profilo">
            </div>
        </div>

        <div class="card">
            <h2>3. File IPA & Installazione</h2>
            <div class="form-group">
                <label>Seleziona il file .IPA:</label>
                <input type="file" id="ipaInput" accept=".ipa">
            </div>

            <button class="btn-primary" id="btnStartResign">⚡ Ri-firma File IPA</button>
            
            <div id="installSection" style="display: none;">
                <button class="btn-install" id="btnInstallOnDevice">📲 Installa Subito su iPhone</button>
                <button class="btn-accent" id="btnDownload">📥 Scarica IPA su Mac</button>
            </div>

            <div class="terminal-box" id="terminalLog">Pronto all'uso. Seleziona l'IPA e procedi.</div>

            <div class="info-tip">
                💡 <b>Installazione Automatica:</b> Il sistema dialoga direttamente con il servizio <code>devicectl</code> di Xcode per caricare l'applicazione direttamente sul tuo iPhone via cavo USB o Wi-Fi, senza dover aprire finestre esterne.
            </div>
        </div>
    </div>

    <script>
        let signedIpaFilename = null;

        const deviceSelect = document.getElementById('deviceSelect');
        const certSelect = document.getElementById('certSelect');
        const profileSelect = document.getElementById('profileSelect');
        const ipaInput = document.getElementById('ipaInput');
        const btnStartResign = document.getElementById('btnStartResign');
        const btnInstallOnDevice = document.getElementById('btnInstallOnDevice');
        const btnDownload = document.getElementById('btnDownload');
        const installSection = document.getElementById('installSection');
        const terminalLog = document.getElementById('terminalLog');

        function appendLog(text) {
            terminalLog.textContent += text + "\\n";
            terminalLog.scrollTop = terminalLog.scrollHeight;
        }

        async function loadDevices() {
            try {
                deviceSelect.innerHTML = '<option value="">Ricerca dispositivi...</option>';
                const res = await fetch('/api/devices');
                const data = await res.json();
                deviceSelect.innerHTML = '';
                if (!data.devices || data.devices.length === 0) {
                    deviceSelect.innerHTML = '<option value="">Nessun dispositivo iOS attivo trovato</option>';
                    return;
                }
                data.devices.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.identifier;
                    const isOnline = d.connected ? '🟢 Collegato (' + d.transport + ')' : '⚪ Non raggiungibile';
                    opt.textContent = `${d.name} (${d.model}) - ${isOnline}`;
                    if (d.connected) opt.selected = true;
                    deviceSelect.appendChild(opt);
                });
            } catch (err) {
                deviceSelect.innerHTML = '<option value="">Errore caricamento dispositivi</option>';
            }
        }

        async function loadCredentials() {
            try {
                const res = await fetch('/api/credentials');
                const data = await res.json();
                
                certSelect.innerHTML = '';
                data.identities.forEach(i => {
                    const opt = document.createElement('option');
                    opt.value = i.name;
                    opt.textContent = `${i.name} (${i.sha1.substring(0, 8)}...)`;
                    certSelect.appendChild(opt);
                });

                profileSelect.innerHTML = '';
                data.profiles.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.path;
                    opt.textContent = `${p.name} [AppID: ${p.app_id}]`;
                    profileSelect.appendChild(opt);
                });
            } catch (err) {
                appendLog("Errore lettura credenziali: " + err);
            }
        }

        document.getElementById('btnRefreshDevices').addEventListener('click', loadDevices);

        btnStartResign.addEventListener('click', async () => {
            const file = ipaInput.files[0];
            if (!file) {
                alert("Seleziona prima un file .IPA!");
                return;
            }
            btnStartResign.disabled = true;
            installSection.style.display = 'none';
            terminalLog.textContent = "";
            appendLog("Avvio procedura di firma profonda...");

            const fd = new FormData();
            fd.append('ipa', file);
            fd.append('identity', certSelect.value);
            fd.append('profile_path', profileSelect.value);
            fd.append('bundle_id', document.getElementById('customBundleId').value);

            try {
                const res = await fetch('/api/resign', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.success) {
                    appendLog(data.log);
                    signedIpaFilename = data.output_filename;
                    installSection.style.display = 'block';
                } else {
                    appendLog(data.log || "Errore durante la firma");
                    alert("Firma fallita. Controlla il log.");
                }
            } catch (err) {
                appendLog("Errore: " + err);
            } finally {
                btnStartResign.disabled = false;
            }
        });

        btnInstallOnDevice.addEventListener('click', async () => {
            const deviceId = deviceSelect.value;
            if (!deviceId) {
                alert("Nessun dispositivo selezionato!");
                return;
            }
            if (!signedIpaFilename) {
                alert("Nessun file IPA firmato disponibile.");
                return;
            }

            btnInstallOnDevice.disabled = true;
            appendLog("\\n⏳ Inizio installazione sul dispositivo: " + deviceId + "...");

            try {
                const res = await fetch('/api/install', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device_id: deviceId, filename: signedIpaFilename })
                });
                const data = await res.json();
                appendLog(data.log);
                if (data.success) {
                    alert("Installazione riuscita! L'app è ora sul tuo iPhone.");
                } else {
                    alert("Errore durante l'installazione. Controlla il log.");
                }
            } catch (err) {
                appendLog("Errore durante l'invio al dispositivo: " + err);
            } finally {
                btnInstallOnDevice.disabled = false;
            }
        });

        btnDownload.addEventListener('click', () => {
            if (signedIpaFilename) {
                window.location.href = '/api/download?file=' + encodeURIComponent(signedIpaFilename);
            }
        });

        window.onload = () => {
            loadDevices();
            loadCredentials();
        };
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/devices")
def get_devices():
    env = os.environ.copy()
    env["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"
    
    tmp_json = "/tmp/detected_ios_devices.json"
    cmd = ["xcrun", "devicectl", "list", "devices", "--json-output", tmp_json]
    try:
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
        if os.path.exists(tmp_json):
            with open(tmp_json) as f:
                data = json.load(f)
            raw_devs = data.get("result", {}).get("devices", [])
            devices = []
            for d in raw_devs:
                props = d.get("deviceProperties", {})
                conn = d.get("connectionProperties", {})
                is_connected = conn.get("transportType") in ["wired", "localNetwork"] and conn.get("pairingState") == "paired"
                devices.append({
                    "identifier": d.get("identifier"),
                    "name": props.get("name", "Dispositivo Apple"),
                    "model": props.get("marketingName", "iPhone/iPad"),
                    "transport": conn.get("transportType", "unknown"),
                    "connected": is_connected
                })
            # Sort connected devices on top
            devices.sort(key=lambda x: not x["connected"])
            return jsonify({"devices": devices})
    except Exception as e:
        pass

    return jsonify({"devices": []})


@app.route("/api/credentials")
def credentials():
    identities = find_signing_identities()
    profiles = find_provisioning_profiles()
    return jsonify({
        "identities": [{"sha1": i.sha1, "name": i.name} for i in identities],
        "profiles": [
            {
                "path": p.path,
                "name": p.name,
                "app_id": p.app_id,
                "expiration": p.expiration,
                "is_wildcard": p.is_wildcard,
            }
            for p in profiles
        ]
    })


@app.route("/api/resign", methods=["POST"])
def resign():
    file = request.files.get("ipa")
    identity = request.form.get("identity")
    profile_path = request.form.get("profile_path")
    bundle_id = request.form.get("bundle_id") or None

    if not file or not identity or not profile_path:
        return jsonify({"success": False, "log": "Parametri incompleti"}), 400

    input_ipa = STORAGE_DIR / f"input_{file.filename}"
    file.save(str(input_ipa))

    out_name = f"signed_{file.filename}"
    output_ipa = STORAGE_DIR / out_name

    logs: list[str] = []

    def logger(msg: str):
        logs.append(msg)

    success = resign_ipa(
        ipa_path=str(input_ipa),
        output_path=str(output_ipa),
        identity_name=identity,
        provision_path=profile_path,
        new_bundle_id=bundle_id,
        log_callback=logger
    )

    user_downloads = Path.home() / "Downloads"
    if success and user_downloads.exists():
        import shutil
        shutil.copy2(str(output_ipa), str(user_downloads / out_name))
        logger(f"\n📁 Copiato automaticamente anche in: ~/Downloads/{out_name}")

    return jsonify({
        "success": success,
        "log": "\n".join(logs),
        "output_filename": out_name if success else None
    })


@app.route("/api/install", methods=["POST"])
def install_on_device():
    data = request.json or {}
    device_id = data.get("device_id")
    filename = data.get("filename")

    if not device_id or not filename:
        return jsonify({"success": False, "log": "Parametri mancanti"}), 400

    ipa_path = STORAGE_DIR / filename
    if not ipa_path.exists():
        return jsonify({"success": False, "log": "File IPA firmato non trovato"}), 404

    env = os.environ.copy()
    env["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"

    cmd = ["xcrun", "devicectl", "device", "install", "app", "--device", device_id, str(ipa_path)]
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        full_log = (res.stdout + "\n" + res.stderr).strip()
        if res.returncode == 0:
            return jsonify({
                "success": True,
                "log": f"✅ Installazione completata con successo sul dispositivo!\n{full_log}"
            })
        else:
            return jsonify({
                "success": False,
                "log": f"❌ Installazione fallita con codice {res.returncode}:\n{full_log}"
            })
    except Exception as e:
        return jsonify({"success": False, "log": f"Errore durante l'installazione: {e}"})


@app.route("/api/download")
def download():
    fname = request.args.get("file")
    if not fname:
        return "File mancante", 400
    target = STORAGE_DIR / fname
    if not target.exists():
        return "File non trovato", 404
    return send_file(str(target), as_attachment=True, download_name=fname)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
