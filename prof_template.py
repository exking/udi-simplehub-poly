import os
import zipfile


DEV_COMMANDS = {
    1: 'ENTER',
    2: 'POWER ON',
    3: 'POWER OFF',
    4: 'POWER TOGGLE',
    5: 'CHANNEL UP',
    6: 'CHANNEL DOWN',
    7: 'PAUSE',
    8: 'PLAY',
    9: 'RECORD',
    10: 'DIGIT 0',
    11: 'DIGIT 1',
    12: 'DIGIT 2',
    13: 'DIGIT 3',
    14: 'DIGIT 4',
    15: 'DIGIT 5',
    16: 'DIGIT 6',
    17: 'DIGIT 7',
    18: 'DIGIT 8',
    19: 'DIGIT 9',
    20: 'STOP',
    21: 'REVERSE',
    22: 'FORWARD',
    23: 'SKIP',
    24: 'VOLUME UP',
    25: 'VOLUME DOWN'
}

NODEDEF_HEADER = """<nodeDefs>

    <nodeDef id="SMPLHUB" nls="SHUB">
        <editors />
        <sts>
            <st id="ST" editor="_2_0_R_0_1" />
        </sts>
        <cmds>
            <sends />
            <accepts>
                <cmd id="DISCOVER" />
            </accepts>
        </cmds>
    </nodeDef>

    <nodeDef id="DEVICE" nls="DEV">
        <editors />
        <sts>
            <st id="ST" editor="DCMD" />
        </sts>
        <cmds>
            <sends />
            <accepts>
                <cmd id="DON" />
                <cmd id="DOF" />
                <cmd id="PTOGGLE" />
                <cmd id="SEND_CMD" init="ST" >
                    <p id="" editor="DCMD" />
                </cmd>
            </accepts>
        </cmds>
    </nodeDef>
"""

NODEDEF_FOOTER = """
</nodeDefs>"""

NLS_HEADER = """# controller
ND-SMPLHUB-NAME = SimpleHub
ND-SMPLHUB-ICON = GenericCtl
CMD-SHUB-DISCOVER-NAME = Re-Discover
ST-SHUB-ST-NAME = NodeServer Online

ST-ROOM-ST-NAME = Last command
CMD-ROOM-SET_ACTIVITY-NAME = Run Activity

# device
ND-DEVICE-NAME = Device
ND-DEVICE-ICON = GenericRsp

ST-DEV-ST-NAME = Last command
CMD-DEV-DON-NAME = Power On
CMD-DEV-DOF-NAME = Power Off
CMD-DEV-PTOGGLE-NAME = Power Toggle
CMD-DEV-SEND_CMD-NAME = Send Command

"""

NLS_FOOTER = """
"""

EDITORS_HEADER = """<editors>
"""

EDITORS_FOOTER = """
</editors>"""

NODEDEF_ROOM_TEMPL = """
    <nodeDef id="ROOM%d" nls="ROOM">
        <editors />
        <sts>
            <st id="ST" editor="R%dCMD" />
        </sts>
        <cmds>
            <sends />
            <accepts>
                <cmd id="SET_ACTIVITY" init="ST" >
                    <p id="" editor="R%dCMD" />
                </cmd>
            </accepts>
        </cmds>
    </nodeDef>
"""

NLS_ROOM_ND_TEMPL = """
ND-ROOM%d-NAME = %s
ND-ROOM%d-ICON = GenericRspCtl
"""

EDITORS_TEMPL = """
  <editor id="R%dCMD">
    <range uom="25" min="%d" max="%d" nls="R%dACT" />
  </editor>
"""

EDITORS_TEMPL_D = """
  <editor id="DCMD">
    <range uom="25" min="1" max="%d" nls="DCMD" />
  </editor>
"""


def extract_index(json):
    try:
        # Also convert to int since update_time will be string.  When comparing
        # strings, "10" is smaller than "2".
        return int(json['idx'])
    except KeyError:
        return 0


def write_nls(file, data):
    file.write(NLS_ROOM_ND_TEMPL % (data['index'], data['name'], data['index']))
    actarray = []
    for act_id, act_data in data['activities'].items():
        actarray.append({ 'ridx': data['index'], 'idx': act_data['index'], 'name': act_data['name']})
        actarray.sort(key=extract_index)
    for nls in actarray:
        file.write('R%dACT-%d = %s\n' % (nls['ridx'], nls['idx'], nls['name']))


def write_room_nd(file, data):
    file.write(NODEDEF_ROOM_TEMPL % (data['index'], data['index'], data['index']))


def write_editor(file, data):
    file.write(EDITORS_TEMPL % (data['index'], 1, len(data['activities']), data['index']))


def write_profile(home=None):
    os.makedirs('profile/nls', exist_ok=True)
    os.makedirs('profile/editor', exist_ok=True)
    os.makedirs('profile/nodedef', exist_ok=True)

    editors_file = open('profile/editor/editors.xml', 'w')
    editors_file.write(EDITORS_HEADER)
    editors_file.write(EDITORS_TEMPL_D % len(DEV_COMMANDS))
    nodedef_file = open('profile/nodedef/nodedefs.xml', 'w')
    nodedef_file.write(NODEDEF_HEADER)
    nls_file = open('profile/nls/en_us.txt', 'w')
    nls_file.write(NLS_HEADER)

    for dcmd_id, dcmd_name in DEV_COMMANDS.items():
        nls_file.write('DCMD-%d = %s\n' % (dcmd_id, dcmd_name))

    if home is not None:
        for room_id, data in home['rooms'].items():
            write_room_nd(nodedef_file, data)
            write_editor(editors_file, data)
            write_nls(nls_file, data)

    nodedef_file.write(NODEDEF_FOOTER)
    nodedef_file.close()
    nls_file.write(NLS_FOOTER)
    nls_file.close()
    editors_file.write(EDITORS_FOOTER)
    editors_file.close()
    write_profile_zip()


def write_profile_zip():
    src = 'profile'
    abs_src = os.path.abspath(src)
    with zipfile.ZipFile('profile.zip', 'w') as zf:
        for dirname, subdirs, files in os.walk(src):
            if '/.' not in dirname:
                for filename in files:
                    if filename.endswith('.xml') or filename.endswith('.txt'):
                        absname = os.path.abspath(os.path.join(dirname, filename))
                        arcname = absname[len(abs_src) + 1:]
                        zf.write(absname, arcname)
        zf.close()
