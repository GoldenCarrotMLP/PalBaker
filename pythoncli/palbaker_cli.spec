# pythoncli/palbaker_cli.spec
# -*- mode: python ; coding: utf-8 -*-

import os

# Define the explicit raw files and folders PyInstaller must bundle into the executable folder
datas = [
    ('plugins', 'plugins'),
    ('deps', 'deps'),
    ('unreal_scripts', 'unreal_scripts'),
    ('utils/blender_utils', 'utils/blender_utils'),
    ('utils/blender_reconstruct.py', 'utils'),
    ('utils/blender_extractor.py', 'utils'),
    ('utils/node_builder.py', 'utils'),
    ('utils/fmodel_helper.py', 'utils'),
    ('utils/image_combiner.py', 'utils'),
    ('ue_import.py', '.'),
    ('ue_export.py', '.')
]

# Dynamically include database JSONs if they have been built locally
if os.path.exists('traits_db.json'):
    datas.append(('traits_db.json', '.'))
if os.path.exists('pal_names_map.json'):
    datas.append(('pal_names_map.json', '.'))

a = Analysis(
    ['palbaker_cli.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uuid',
        'socket',
        'select',
        'struct',
        'logging'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='palbaker_cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='palbaker_cli',
)