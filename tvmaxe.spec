# -*- mode: python -*-

import shutil

block_cipher = None

a = Analysis(['tv-maxe/tvmaxe.py'],
             pathex=['tv-maxe/'],
             binaries=[(shutil.which('sp-sc'), '.')],
             datas=[('tv-maxe/icons', 'icons'),
                    ('tv-maxe/images', 'images'),
                    ('tv-maxe/models', 'models'),
                    ('tv-maxe/protocols', 'protocols'),
                    ('tv-maxe/ui', 'ui'),
                    ('tv-maxe/i18n/*.qm', 'i18n')],
             hiddenimports=['librtmp', 'videoplayer', 'channellistwidget', 'elidedlabel', 'appdirs', 
                            'packaging', 'packaging.version', 'packaging.specifiers', 'packaging.requirements'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='tvmaxe',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='tvmaxe')
app = BUNDLE(exe,
         name='TV-Maxe.app',
         icon='tv-maxe/icons/tvmaxe.icns',
         bundle_identifier='org.tv-maxe.desktop')