# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../../kuttypets/main.py'],
    pathex=['../../'],
    binaries=[],
    datas=[('../../kuttypets/characters', 'kuttypets/characters')],
    hiddenimports=[
        'win32gui', 'win32con', 'ctypes', 'winreg',
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PIL', 'PIL.Image',
        'kuttypets', 'kuttypets.config', 'kuttypets.core',
        'kuttypets.core.engine', 'kuttypets.core.rigs',
        'kuttypets.core.kinematics', 'kuttypets.core.web_physics',
        'kuttypets.core.autostart', 'kuttypets.adapters',
        'kuttypets.adapters.base', 'kuttypets.adapters.win32_adapter',
        'kuttypets.render', 'kuttypets.render.canvas',
        'kuttypets.render.particles', 'kuttypets.render.shadows',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KuttyPets',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
