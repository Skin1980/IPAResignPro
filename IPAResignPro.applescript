-- IPAResign Pro - Native AppleScript Droplet Application
-- 100% native macOS Cocoa dialogs, zero Python dependencies, runs on EVERY Mac!

on run
	set userHome to POSIX path of (path to home folder)
	set chosenFile to choose file with prompt "Seleziona il file .IPA da ri-firmare:" of type {"ipa", "zip"} default location (POSIX file (userHome & "Downloads/"))
	processIPA(POSIX path of chosenFile)
end run

on open droppedFiles
	repeat with oneFile in droppedFiles
		set posixPath to POSIX path of oneFile
		if posixPath ends with ".ipa" or posixPath ends with ".IPA" then
			processIPA(posixPath)
			return
		end if
	end repeat
	display alert "Attenzione" message "Trascina un file valido con estensione .ipa" as warning
end open

on processIPA(ipaPath)
	-- 1. Find Identities
	set identsRaw to do shell script "security find-identity -v -p codesigning | grep ')' | sed -E 's/.*\"(.*)\"/\\1/'"
	set identsList to paragraphs of identsRaw
	
	if (count of identsList) is 0 then
		display alert "Errore Certificato" message "Nessun certificato Apple Developer trovato nel Portachiavi." as critical
		return
	end if
	
	set chosenCert to choose from list identsList with prompt "1. Seleziona il Certificato Apple:" default items {item 1 of identsList} with title "IPAResign Pro"
	if chosenCert is false then return
	set certName to item 1 of chosenCert
	
	-- 2. Find Provisioning Profiles
	set profsRaw to do shell script "python3 -c \"
import glob, os, subprocess, plistlib
search_dirs = [os.path.expanduser('~/Library/MobileDevice/Provisioning Profiles'), os.path.expanduser('~/Library/Developer/Xcode/DerivedData')]
files = []
for d in search_dirs:
    if os.path.exists(d): files.extend(glob.glob(d + '/**/*.mobileprovision', recursive=True))
profs = {}
for f in files:
    try:
        data = plistlib.loads(subprocess.check_output(['security', 'cms', '-D', '-i', f], stderr=subprocess.DEVNULL))
        name = data.get('Name', 'Unknown')
        app_id = data.get('Entitlements', {}).get('application-identifier', '')
        exp = str(data.get('ExpirationDate', '')).split()[0]
        profs[f'{name} [{app_id}] (Scad: {exp})'] = f
    except: pass
for k, v in profs.items():
    print(k + '@@@' + v)
\""
	
	set profLines to paragraphs of profsRaw
	set profNames to {}
	set profPaths to {}
	
	repeat with aLine in profLines
		if aLine contains "@@@" then
			set AppleScript's text item delimiters to "@@@"
			set end of profNames to text item 1 of aLine
			set end of profPaths to text item 2 of aLine
		end if
	end repeat
	
	if (count of profNames) is 0 then
		display alert "Errore Profilo" message "Nessun Provisioning Profile trovato in Xcode. Compila prima un'app di prova su Xcode." as critical
		return
	end if
	
	set chosenProf to choose from list profNames with prompt "2. Seleziona il Provisioning Profile di Xcode:" default items {item 1 of profNames} with title "IPAResign Pro"
	if chosenProf is false then return
	set profLabel to item 1 of chosenProf
	
	-- Get matching path
	repeat with i from 1 to count of profNames
		if item i of profNames is profLabel then
			set targetProfPath to item i of profPaths
			exit repeat
		end if
	end repeat
	
	-- 3. Ask destination
	set userHome to POSIX path of (path to home folder)
	set defaultOut to userHome & "Downloads/signed_" & do shell script "basename " & quoted form of ipaPath
	
	display dialog "Pronto per avviare la firma profonda ricorsiva!\n\nFile IPA: " & ipaPath & "\nCertificato: " & certName with title "IPAResign Pro" buttons {"Annulla", "⚡ Avvia Firma"} default button "⚡ Avvia Firma"
	
	-- Run python resign engine
	display notification "Firma in corso... L'operazione potrebbe richiedere 15-30 secondi." with title "IPAResign Pro"
	
	set resignScript to "python3 -c \"
import sys, subprocess, os, plistlib, tempfile, shutil, glob
from pathlib import Path

ipa_path = sys.argv[1]
out_path = sys.argv[2]
identity = sys.argv[3]
profile_path = sys.argv[4]

work_dir = Path(tempfile.mkdtemp(prefix='ipa_mac_'))
try:
    subprocess.check_call(['unzip', '-q', ipa_path, '-d', str(work_dir)])
    payload = work_dir / 'Payload'
    app_dir = list(payload.glob('*.app'))[0]

    cms_out = subprocess.check_output(['security', 'cms', '-D', '-i', profile_path])
    p_dict = plistlib.loads(cms_out)
    ent_dict = p_dict.get('Entitlements', {})
    team_id = p_dict.get('TeamIdentifier', [''])[0] if p_dict.get('TeamIdentifier') else ''
    app_id_target = ent_dict.get('application-identifier', '')

    info_plist_path = app_dir / 'Info.plist'
    with open(info_plist_path, 'rb') as fp:
        info_data = plistlib.load(fp)

    orig_bundle_id = info_data.get('CFBundleIdentifier', '')
    if '*' in app_id_target:
        final_bundle_id = orig_bundle_id
    else:
        prefix = f'{team_id}.'
        final_bundle_id = app_id_target[len(prefix):] if app_id_target.startswith(prefix) else app_id_target

    info_data['CFBundleIdentifier'] = final_bundle_id
    with open(info_plist_path, 'wb') as fp:
        plistlib.dump(info_data, fp)

    shutil.copy2(profile_path, app_dir / 'embedded.mobileprovision')
    ent_file = work_dir / 'entitlements.plist'
    with open(ent_file, 'wb') as fp:
        plistlib.dump(ent_dict, fp)

    for sig in app_dir.glob('**/_CodeSignature'):
        if sig.is_dir(): shutil.rmtree(sig)

    for dylib in app_dir.glob('**/*.dylib'):
        subprocess.check_call(['codesign', '-f', '-s', identity, '--timestamp=none', str(dylib)])

    for fw in sorted(list(app_dir.glob('**/*.framework')), key=lambda p: len(str(p)), reverse=True):
        subprocess.check_call(['codesign', '-f', '-s', identity, '--timestamp=none', str(fw)])

    for appex in app_dir.glob('**/*.appex'):
        shutil.copy2(profile_path, appex / 'embedded.mobileprovision')
        subprocess.check_call(['codesign', '-f', '-s', identity, '--entitlements', str(ent_file), '--timestamp=none', str(appex)])

    subprocess.check_call(['codesign', '-f', '-s', identity, '--entitlements', str(ent_file), '--timestamp=none', str(app_dir)])

    out_ipa = Path(out_path).resolve()
    if out_ipa.exists(): out_ipa.unlink()
    cwd = os.getcwd()
    try:
        os.chdir(str(work_dir))
        subprocess.check_call(['zip', '-qr', str(out_ipa), 'Payload'])
    finally:
        os.chdir(cwd)
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(work_dir, ignore_errors=True)
\" " & quoted form of ipaPath & " " & quoted form of defaultOut & " " & quoted form of certName & " " & quoted form of targetProfPath
	
	try
		set resCmd to do shell script resignScript
	on error errMsg
		display alert "Errore durante la firma" message errMsg as critical
		return
	end try
	
	-- 4. Check connected devices for optional 1-click install
	set devRaw to do shell script "DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer python3 -c \"
import json, subprocess
cmd = ['xcrun', 'devicectl', 'list', 'devices', '--json-output', '/tmp/applet_devs.json']
try:
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    with open('/tmp/applet_devs.json') as f: data = json.load(f)
    for d in data.get('result', {}).get('devices', []):
        conn = d.get('connectionProperties', {})
        if conn.get('transportType') in ['wired', 'localNetwork'] and conn.get('pairingState') == 'paired':
            print(d.get('identifier') + '@@@' + d.get('deviceProperties', {}).get('name', 'iPhone') + ' (' + conn.get('transportType') + ')')
except: pass
\""
	
	set devLines to paragraphs of devRaw
	if (count of devLines) > 0 and (item 1 of devLines contains "@@@") then
		set AppleScript's text item delimiters to "@@@"
		set devId to text item 1 of (item 1 of devLines)
		set devName to text item 2 of (item 1 of devLines)
		
		set askInstall to display dialog "🎉 IPA Firmato con successo!\n\nSalvato in:\n" & defaultOut & "\n\nVuoi installarlo subito su: " & devName & "?" with title "IPAResign Pro" buttons {"Solo Salva", "📲 Installa su " & devName} default button "📲 Installa su " & devName
		
		if button returned of askInstall contains "Installa" then
			display notification "Installazione in corso sull'iPhone..." with title "IPAResign Pro"
			set installCmd to "DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcrun devicectl device install app --device " & devId & " " & quoted form of defaultOut
			try
				do shell script installCmd
				display alert "Installazione Completata!" message "L'app è stata installata con successo sul tuo iPhone!" as informational
			on error instErr
				display alert "Errore Installazione" message instErr as critical
			end try
		end if
	else
		display alert "Firma Completata!" message "IPA firmato con successo e salvato in:\n" & defaultOut as informational
	end if
	
end processIPA
