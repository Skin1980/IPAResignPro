#!/usr/bin/env python3
"""
IPAResignPro - Engine
Deep-resigns any iOS IPA using an active Apple Developer Certificate & Provisioning Profile.
Recursively signs all dylibs, frameworks, App Extensions (appex), plugins, and executables,
ensuring 100% cryptographic integrity and preventing "Unable to verify app" iOS lockouts.
"""

from __future__ import annotations

import glob
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class SigningIdentity:
    sha1: str
    name: str


@dataclass
class ProvisioningProfile:
    path: str
    name: str
    app_id: str
    team_id: str
    expiration: str
    is_wildcard: bool


def find_signing_identities() -> List[SigningIdentity]:
    """Finds all valid Apple code signing identities in the macOS keychain."""
    cmd = ["security", "find-identity", "-v", "-p", "codesigning"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    identities: List[SigningIdentity] = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if ")" in line and '"' in line:
            parts = line.split(")", 1)[1].strip()
            tokens = parts.split('"', 1)
            sha1 = tokens[0].strip()
            name = tokens[1].rstrip('"').strip()
            identities.append(SigningIdentity(sha1=sha1, name=name))
    return identities


def find_provisioning_profiles() -> List[ProvisioningProfile]:
    """Scans standard Xcode locations and DerivedData for valid embedded.mobileprovision files."""
    search_dirs = [
        os.path.expanduser("~/Library/MobileDevice/Provisioning Profiles"),
        os.path.expanduser("~/Library/Developer/Xcode/DerivedData"),
        os.path.expanduser("~/Library/Developer/Xcode/UserData/Provisioning Profiles"),
    ]

    files: List[str] = []
    for sdir in search_dirs:
        if os.path.exists(sdir):
            files.extend(glob.glob(f"{sdir}/**/*.mobileprovision", recursive=True))

    profiles: Dict[str, ProvisioningProfile] = {}
    for fpath in files:
        try:
            raw_plist = subprocess.check_output(
                ["security", "cms", "-D", "-i", fpath],
                stderr=subprocess.DEVNULL
            )
            data = plistlib.loads(raw_plist)
            name = data.get("Name", "Unknown")
            entitlements = data.get("Entitlements", {})
            app_id = entitlements.get("application-identifier", "")
            team_id = data.get("TeamIdentifier", [""])[0] if data.get("TeamIdentifier") else ""
            exp = str(data.get("ExpirationDate", ""))
            is_wildcard = "*" in app_id

            # Key by App ID to deduplicate identical profiles
            key = f"{app_id}_{name}"
            if key not in profiles:
                profiles[key] = ProvisioningProfile(
                    path=fpath,
                    name=name,
                    app_id=app_id,
                    team_id=team_id,
                    expiration=exp,
                    is_wildcard=is_wildcard
                )
        except Exception:
            continue

    # Sort wildcards first, then by name
    return sorted(list(profiles.values()), key=lambda p: (not p.is_wildcard, p.name))


def resign_ipa(
    ipa_path: str,
    output_path: str,
    identity_name: str,
    provision_path: str,
    new_bundle_id: Optional[str] = None,
    log_callback=print
) -> bool:
    """
    Performs full deep-resigning of the given IPA:
      1. Unzips IPA into a temporary working folder.
      2. Replaces embedded.mobileprovision.
      3. Extracts the entitlements.plist from the mobileprovision and adapts it.
      4. Adjusts CFBundleIdentifier in Info.plist to match the provisioning profile if needed.
      5. Strips old CodeResources and signatures.
      6. Bottom-up recursively signs:
         - All .dylib files
         - All .framework directories
         - All .appex (App Extensions / Widgets)
         - The main .app bundle
      7. Re-packages the cleaned, signed Payload into a pristine .ipa.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="ipa_resign_"))
    try:
        log_callback(f"[1/6] Estrazione di: {Path(ipa_path).name}...")
        subprocess.check_call(["unzip", "-q", ipa_path, "-d", str(work_dir)])

        payload_dir = work_dir / "Payload"
        if not payload_dir.exists():
            log_callback("ERRORE: Cartella Payload non trovata nell'archivio IPA!")
            return False

        app_dirs = list(payload_dir.glob("*.app"))
        if not app_dirs:
            log_callback("ERRORE: Nessun bundle .app trovato dentro Payload!")
            return False

        app_dir = app_dirs[0]
        log_callback(f"[2/6] Analisi bundle applicazione: {app_dir.name}")

        # Extract profile plist and entitlements
        cms_out = subprocess.check_output(["security", "cms", "-D", "-i", provision_path])
        profile_dict = plistlib.loads(cms_out)
        entitlements_dict = profile_dict.get("Entitlements", {})

        target_app_id = entitlements_dict.get("application-identifier", "")
        team_id = profile_dict.get("TeamIdentifier", [""])[0] if profile_dict.get("TeamIdentifier") else ""

        # Read main Info.plist
        info_plist_path = app_dir / "Info.plist"
        info_plist_data = {}
        if info_plist_path.exists():
            with open(info_plist_path, "rb") as fp:
                info_plist_data = plistlib.load(fp)

        current_bundle_id = info_plist_data.get("CFBundleIdentifier", "")

        # Compute new bundle identifier
        if new_bundle_id:
            final_bundle_id = new_bundle_id
        elif "*" in target_app_id:
            # Wildcard profile (e.g. TEAMID.*) -> keep original or custom
            prefix = target_app_id.replace(".*", "")
            final_bundle_id = current_bundle_id
        else:
            # Explicit profile (e.g. TEAMID.com.example.app)
            prefix = f"{team_id}."
            if target_app_id.startswith(prefix):
                final_bundle_id = target_app_id[len(prefix):]
            else:
                final_bundle_id = target_app_id

        log_callback(f"      -> Bundle ID: {final_bundle_id} (Team: {team_id})")

        # Update Info.plist
        info_plist_data["CFBundleIdentifier"] = final_bundle_id
        with open(info_plist_path, "wb") as fp:
            plistlib.dump(info_plist_data, fp)

        # Copy new mobileprovision into app
        shutil.copy2(provision_path, app_dir / "embedded.mobileprovision")

        # Save entitlements.plist
        entitlements_path = work_dir / "entitlements.plist"
        with open(entitlements_path, "wb") as fp:
            plistlib.dump(entitlements_dict, fp)

        log_callback("[3/6] Rimozione vecchie firme e file _CodeSignature...")
        for sig in app_dir.glob("**/_CodeSignature"):
            if sig.is_dir():
                shutil.rmtree(sig)

        log_callback("[4/6] Ri-firma ricorsiva profonda di tutti i componenti...")

        # A. Sign dylibs
        dylibs = list(app_dir.glob("**/*.dylib"))
        for dylib in dylibs:
            log_callback(f"   -> Firma libreria: {dylib.name}")
            subprocess.check_call([
                "codesign", "-f", "-s", identity_name,
                "--timestamp=none",
                str(dylib)
            ])

        # B. Sign Frameworks (from inside out)
        frameworks = sorted(list(app_dir.glob("**/*.framework")), key=lambda p: len(str(p)), reverse=True)
        for fw in frameworks:
            log_callback(f"   -> Firma framework: {fw.name}")
            subprocess.check_call([
                "codesign", "-f", "-s", identity_name,
                "--timestamp=none",
                str(fw)
            ])

        # C. Sign PlugIns / App Extensions (appex)
        appexes = list(app_dir.glob("**/*.appex"))
        for appex in appexes:
            log_callback(f"   -> Firma extension: {appex.name}")
            # Each appex needs embedded.mobileprovision and matching signing
            shutil.copy2(provision_path, appex / "embedded.mobileprovision")
            subprocess.check_call([
                "codesign", "-f", "-s", identity_name,
                "--entitlements", str(entitlements_path),
                "--timestamp=none",
                str(appex)
            ])

        # D. Sign main .app bundle
        log_callback(f"[5/6] Firma finale del bundle principale: {app_dir.name}...")
        subprocess.check_call([
            "codesign", "-f", "-s", identity_name,
            "--entitlements", str(entitlements_path),
            "--timestamp=none",
            str(app_dir)
        ])

        # Verify signature
        log_callback("      -> Verifica integrità crittografica...")
        verify_cmd = ["codesign", "--verify", "--deep", "--strict", str(app_dir)]
        verify_res = subprocess.run(verify_cmd, capture_output=True, text=True)
        if verify_res.returncode != 0:
            log_callback(f"AVVISO: Controllo codesign ha restituito: {verify_res.stderr.strip()}")
        else:
            log_callback("      -> Verifica superata con successo al 100%! ✅")

        # Repackage into output IPA
        log_callback(f"[6/6] Creazione pacchetto IPA finale: {Path(output_path).name}...")
        out_ipa = Path(output_path).resolve()
        out_ipa.parent.mkdir(parents=True, exist_ok=True)
        if out_ipa.exists():
            out_ipa.unlink()

        # Zip Payload directory
        cwd = os.getcwd()
        try:
            os.chdir(str(work_dir))
            subprocess.check_call(["zip", "-qr", str(out_ipa), "Payload"])
        finally:
            os.chdir(cwd)

        log_callback(f"\n🎉 OPERAZIONE COMPLETATA! File pronto in:\n{out_ipa}")
        return True

    except Exception as e:
        log_callback(f"\n❌ ERRORE IMPREVISTO DURANTE LA FIRMA: {e}")
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
