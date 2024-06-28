# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules
import tomli


with open('config.toml', 'rb') as fp:
    CFG = tomli.load(fp)

IMAGE_PROVIDER = CFG.get('IMAGE_PROVIDER', "cv2").lower()
VIDEO_PROVIDER = CFG.get('VIDEO_PROVIDER', "cv2").lower()


if VIDEO_PROVIDER == 'av':
    if IMAGE_PROVIDER == 'pillow':
        image_provider = 'modules.rtsp.av_pil'
    elif IMAGE_PROVIDER == 'cv2':
        image_provider = 'modules.rtsp.av_cv2'
    else:
        raise ImportError("Wrong image provider for PyAV backend")
elif VIDEO_PROVIDER == 'cv2' and IMAGE_PROVIDER == 'cv2':
    image_provider = 'modules.rtsp.cv2'
else:
    raise ImportError("Wrong image provider for cv2 backend")

hiddenimports=collect_submodules('uvicorn')
hiddenimports += [
    image_provider,
    'pywintypes',
    'pythoncom',
    'pywin',
    'rtsp_cv2',
]

block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('pwa', 'pwa'),
        ('config.toml', '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'Pillow',
        'PIL',
        'setuptools',
        'wheel',
        'email_validator',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ArcherLinkPWA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version.txt',
    icon='icon.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ArcherLinkPWA',
)
