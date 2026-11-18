# -*- coding: utf-8 -*-
"""
MehburAI - Windows sürüm bilgisi (version resource) üretici
=============================================================
İmzasız derlenen .exe'lerde Yayımcı/Ürün adı/Açıklama gibi Win32 "sürüm
bilgisi" alanlarının BOŞ olması, SmartScreen/antivirüslerin sezgisel
(heuristic) tespitinde ekstra bir şüphe işaretidir — gerçek yazılımların
neredeyse tamamında bu alanlar doludur. Bu dosya derlenen .exe'lere
gömülecek `VSVersionInfo` nesnesini üretir (`MehburAI.spec` doğrudan,
`build_exe.bat`'teki Setup derlemesi `--version-file` ile statik bir .txt
üzerinden kullanır — PyInstaller'ın CLI'si yalnız dosya yolu kabul eder).

Bu, SmartScreen/antivirüs yanlış pozitiflerini KESİN çözmez (bunun tek
kesin çözümü ücretli bir kod imzalama sertifikasıdır) ama ücretsiz, zararsız
ve tespit oranını azaltan bilinen bir iyileştirmedir.
"""

import re


def _version_tuple(version_str: str):
    """'1.6.1' → (1, 6, 1, 0) — Win32 sürüm alanı her zaman 4 sayı ister."""
    parts = [int(p) for p in re.findall(r"\d+", version_str)][:4]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def build_version_info(version: str, file_description: str, original_filename: str,
                        internal_name: str = "MehburAI", product_name: str = "MehburAI"):
    """PyInstaller `EXE(version=...)`'a doğrudan verilebilecek bir VSVersionInfo nesnesi döndürür."""
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
    )
    vt = _version_tuple(version)
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=vt, prodvers=vt, mask=0x3F, flags=0x0,
                          OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "Mehbur07"),
                StringStruct("FileDescription", file_description),
                StringStruct("FileVersion", version),
                StringStruct("InternalName", internal_name),
                StringStruct("LegalCopyright", "Mehbur07 — Acik kaynak (MIT Lisansi)"),
                StringStruct("OriginalFilename", original_filename),
                StringStruct("ProductName", product_name),
                StringStruct("ProductVersion", version),
            ])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )


if __name__ == "__main__":
    # CLI: statik bir .txt sürüm dosyası yazar — PyInstaller'ın `--version-file <yol>`
    # bayrağı yalnız dosya yolu kabul eder, canlı Python nesnesi değil.
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--filename", required=True, help="OriginalFilename, örn. MehburAI.Setup.exe")
    p.add_argument("--out", required=True)
    p.add_argument("--internal-name", default="MehburAI")
    p.add_argument("--product-name", default="MehburAI")
    args = p.parse_args()

    info = build_version_info(args.version, args.description, args.filename,
                              args.internal_name, args.product_name)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(str(info))
    print(f"Sürüm bilgisi yazıldı: {args.out}")
