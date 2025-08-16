# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['proxy_interceptor/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/or-proxy.icns', 'assets'),
        ('assets/*.png', 'assets'),
    ],
    hiddenimports=[
        'proxy_interceptor.main_window',
        'proxy_interceptor.proxy_server',
        'proxy_interceptor.models',
        'proxy_interceptor.request_list_widget',
        'proxy_interceptor.request_details_widget',
        'proxy_interceptor.config_widget',
        'proxy_interceptor.model_selection_widget',
        'proxy_interceptor.cheatsheet_widget',
        'proxy_interceptor.styles',
        'proxy_interceptor.error_utils',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan.on',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
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
    name='OpenRouterProxy',
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
    icon='assets/or-proxy.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OpenRouterProxy',
)

app = BUNDLE(
    coll,
    name='OpenRouterProxy.app',
    icon='assets/or-proxy.icns',
    bundle_identifier='dev.deskriders.openrouter-proxy',
    info_plist={
        'CFBundleName': 'OpenRouterProxy',
        'CFBundleDisplayName': 'OpenRouterProxy',
        'CFBundleIdentifier': 'dev.deskriders.openrouter-proxy',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleExecutable': 'OpenRouterProxy',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'ORPX',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.15.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 Namuan. All rights reserved.',
        'CFBundleDocumentTypes': [],
        'NSPrincipalClass': 'NSApplication',
    },
)